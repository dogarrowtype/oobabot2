# -*- coding: utf-8 -*-
"""
Contains all runtime state of the bot.
"""

import asyncio
from concurrent import futures
import contextlib
import os
import threading
import typing

import discord

from oobabot import bot_commands
from oobabot import decide_to_respond
from oobabot import discord_bot
from oobabot import fancy_logger
from oobabot import http_client
from oobabot import image_generator
from oobabot import ooba_client
from oobabot import persona
from oobabot import prompt_generator
from oobabot import repetition_tracker
from oobabot import response_stats
from oobabot import sd_client
from oobabot import settings
from oobabot import templates
from oobabot import vision


class OobabotRuntimeError(Exception):
    """
    Raised when the bot encounters an error that it can't recover from.
    """


class Runtime:
    """
    Contains all the runtime state of the bot. It should be
    created once the configuration is known.
    """

    DISCORD_TOKEN_ENV_VAR: str = "DISCORD_TOKEN"

    def __init__(self, settings: settings.Settings):
        # templates used to generate prompts to send to the AI
        # as well as for some UI elements
        self.template_store = templates.TemplateStore(
            settings=settings.template_settings.get_all()
        )

        ########################################################
        # Connect to Oobabooga

        self.ooba_client = ooba_client.OobaClient(
            settings=settings.oobabooga_settings.get_all(),
            template_store = self.template_store,
        )

        ########################################################
        # Connect to Stable Diffusion, if configured

        self.stable_diffusion_client: typing.Optional[
            sd_client.StableDiffusionClient
        ] = None
        sd_settings = settings.stable_diffusion_settings.get_all()
        if sd_settings["stable_diffusion_url"]:
            self.stable_diffusion_client = sd_client.StableDiffusionClient(
                settings=sd_settings,
                magic_model_key=settings.SD_CLIENT_MAGIC_MODEL_KEY,
            )

        ########################################################
        # Bot logic

        self.persona = persona.Persona(
            persona_settings=settings.persona_settings.get_all()
        )

        # decides which messages the bot will respond to
        self.decide_to_respond = decide_to_respond.DecideToRespond(
            discord_settings=settings.discord_settings.get_all(),
            persona=self.persona,
        )

        # once we decide to respond, this generates a prompt
        # to send to the AI, given a message history
        self.prompt_generator = prompt_generator.PromptGenerator(
            discord_settings=settings.discord_settings.get_all(),
            oobabooga_settings=settings.oobabooga_settings.get_all(),
            persona=self.persona,
            template_store=self.template_store,
            ooba_client=self.ooba_client,
        )

        # tracks of the time spent on responding, success rate, etc.
        self.response_stats = response_stats.AggregateResponseStats(
            fn_get_total_tokens=lambda: self.ooba_client.total_response_tokens
        )

        # generates images, if stable diffusion is configured
        # also includes a UI to regenerate images on demand
        self.image_generator = None
        if self.stable_diffusion_client:
            self.image_generator = image_generator.ImageGenerator(
                ooba_client=self.ooba_client,
                persona_settings=settings.persona_settings.get_all(),
                prompt_generator=self.prompt_generator,
                sd_settings=settings.stable_diffusion_settings.get_all(),
                stable_diffusion_client=self.stable_diffusion_client,
                template_store=self.template_store,
            )

        # converts images into text descriptions so the bot can understand the contents
        self.vision = None
        vision_settings = settings.vision_api_settings.get_all()
        if vision_settings["vision_api_url"]:
            self.vision = vision.VisionClient(
                settings=vision_settings,
                persona=self.persona,
                template_store=self.template_store
            )

        # if a bot sees itself repeating a message over and over,
        # it will keep doing so forever. This attempts to fix that.
        # by looking for repeated responses, and deciding how far
        # back in history the bot can see.
        self.repetition_tracker = repetition_tracker.RepetitionTracker(
            repetition_threshold=settings.REPETITION_TRACKER_THRESHOLD
        )

        self.bot_commands = bot_commands.BotCommands(
            decide_to_respond=self.decide_to_respond,
            repetition_tracker=self.repetition_tracker,
            persona=self.persona,
            discord_settings=settings.discord_settings.get_all(),
            template_store=self.template_store,
            ooba_client=self.ooba_client,
            prompt_generator=self.prompt_generator,
        )

        ########################################################
        # Connect to Discord

        self.discord_settings = settings.discord_settings.get_all()

        env_discord_token = os.environ.get(settings.DISCORD_TOKEN_ENV_VAR, "")
        if env_discord_token:
            self.discord_settings["discord_token"] = env_discord_token
        if not self.discord_settings.get("discord_token", ""):
            raise ValueError(
                f"Please set the '{self.DISCORD_TOKEN_ENV_VAR}' "
                + "environment variable to your bot's discord token,"
                + "or place the token in the configuration file."
            )

        self.discord_bot = discord_bot.DiscordBot(
            bot_commands=self.bot_commands,
            decide_to_respond=self.decide_to_respond,
            discord_settings=self.discord_settings,
            ooba_client=self.ooba_client,
            image_generator=self.image_generator,
            vision_client=self.vision,
            persona=self.persona,
            template_store=self.template_store,
            prompt_generator=self.prompt_generator,
            repetition_tracker=self.repetition_tracker,
            response_stats=self.response_stats,
        )

    def test_connections(self) -> typing.Tuple[bool, bool]:
        """
        Tests that we can connect to all services we depend on.
        Does not test Discord connectivity.

        Returns True if all configured connections succeeded,
        False otherwise.
        """

        for client in [self.ooba_client, self.stable_diffusion_client]:
            if not client:
                continue

            fancy_logger.get().info("%s is at %s", client.service_name, client.base_url)
            try:
                client.test_connection()
                fancy_logger.get().info("Connected to %s!", client.service_name)
            except (ValueError, http_client.OobaHttpClientError) as err:
                fancy_logger.get().warning(
                    "Could not connect to %s server: [%s]",
                    client.service_name,
                    client.base_url,
                )
                fancy_logger.get().warning("Please check the URL and try again.")
                if str(err.__cause__):
                    fancy_logger.get().error("Reason: %s", err.__cause__)
                return client is self.ooba_client, False
        return client is self.ooba_client, True

    async def run(self):
        """
        Opens HTTP connections to oobabooga and stable diffusion,
        then connects to Discord. Blocks until the bot is stopped.

        Raises OobabotRuntimeError if the bot cannot connect to Discord.
        """

        async with contextlib.AsyncExitStack() as stack:
            for context_manager in [
                self.ooba_client,
                self.stable_diffusion_client,
            ]:
                if context_manager:
                    await stack.enter_async_context(context_manager)

            discord_token = str(self.discord_settings["discord_token"])
            try:
                fancy_logger.get().info("Connecting to Discord... ")
                await self.discord_bot.start(discord_token)
                fancy_logger.get().info("Discord bot exited.")

            except discord.errors.PrivilegedIntentsRequired as err:
                fancy_logger.get().warning("Could not log in to Discord: %s", err)
                fancy_logger.get().warning(
                    "The bot token you provided does not have the required "
                    + "gateway intents. Did you remember to enable both "
                    + "'SERVER MEMBERS INTENT' and 'MESSAGE CONTENT INTENT' "
                    + "in the bot's settings on Discord?"
                )
                raise OobabotRuntimeError(
                    "Could not log in to Discord: intents not set"
                ) from err

            except discord.LoginFailure as err:
                fancy_logger.get().warning("Could not log in to Discord: %s", err)
                fancy_logger.get().warning("Please check the token and try again.")
                raise OobabotRuntimeError(
                    "Could not log in to Discord: invalid token"
                ) from err

            finally:
                await self.discord_bot.close()
        fancy_logger.get().info("Disconnected from Discord.")

    def stop(self, wait_timeout: float = 5.0) -> None:
        """
        Stops the bot, if it's running. Safe to be called
        from a separate thread from the one that called run().

        Blocks until the bot is gracefully stopped, or until
        wait_timeout seconds have passed, whichever comes first.
        """

        self.response_stats.write_stat_summary_to_log()

        # if we're on our main thread, then we can just terminate
        # the bot loop directly. But if we're on a separate thread,
        # then we need to call it from the  discord bot's event loop.
        if threading.current_thread() == threading.main_thread():
            self.discord_bot.loop.stop()
            return

        try:
            # if discord is already stopped, then their .loop is set
            # _MissingSentinel. So instead check if it's still connected.
            if self.discord_bot.is_closed():
                fancy_logger.get().info("Discord bot already stopped.")
                return

            future = asyncio.run_coroutine_threadsafe(
                self.discord_bot.close(),
                self.discord_bot.loop,
            )
            future.result(timeout=wait_timeout)
        except RuntimeError as err:
            # this can happen if the main application is shutting down
            fancy_logger.get().error("Could not stop Discord bot: %s", err)
            raise OobabotRuntimeError("Discord bot is already stopped.") from err
        except futures.TimeoutError:
            fancy_logger.get().warning(
                "Discord bot did not stop in time, it might be busted."
            )
