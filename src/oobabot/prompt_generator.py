# -*- coding: utf-8 -*-
"""
Generate a prompt for the AI to respond to, given the
message history and persona.
"""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import typing
from oobabot import fancy_logger
from oobabot import ooba_client
from oobabot import persona
from oobabot import templates
from oobabot import types


class PromptGenerator:
    """
    Purpose: generate a prompt for the AI to use, given
    the message history and persona.
    """

    # this is set by the AI, and is the maximum length
    # it will understand before it starts to ignore
    # the rest of the prompt_prefix
    # note: we don't currently measure tokens, we just
    # count characters. This is a rough estimate.
    EST_CHARACTERS_PER_TOKEN = 3

    # the estimated number of characters in a line of message history
    # this is used to roughly calculate whether we'll have enough space
    # to supply the requested number of lines of history.
    #
    # in practice, we will look at the actual number of characters to
    # see what we can fit.
    #
    # note that we're doing calculations in characters, not in tokens,
    # so even counting characters exactly is still an estimate.
    EST_CHARACTERS_PER_HISTORY_LINE = 30

    # when we're not splitting responses, each history line is
    # much larger, and it's easier to run out of token space,
    # so we use a different estimate
    EST_CHARACTERS_PER_HISTORY_LINE_NOT_SPLITTING_RESPONSES = 180

    def __init__(
        self,
        discord_settings: dict,
        oobabooga_settings: dict,
        persona: persona.Persona,
        template_store: templates.TemplateStore,
        ooba_client: ooba_client.OobaClient,
    ):
        self.persona = persona
        self.template_store = template_store
        self.ooba_client = ooba_client
        self.dont_split_responses = discord_settings["dont_split_responses"]
        self.reply_in_thread = discord_settings["reply_in_thread"]
        self.history_lines = discord_settings["history_lines"]
        self.token_space = oobabooga_settings["request_params"]["truncation_length"]

        self.example_dialogue = self.template_store.format(
            templates.Templates.EXAMPLE_DIALOGUE,
            {
                templates.TemplateToken.USER_SEQUENCE_PREFIX: self.template_store.format(
                    templates.Templates.USER_SEQUENCE_PREFIX,
                    {},
                ),
                templates.TemplateToken.USER_SEQUENCE_SUFFIX: self.template_store.format(
                    templates.Templates.USER_SEQUENCE_SUFFIX,
                    {},
                ),
                templates.TemplateToken.BOT_SEQUENCE_PREFIX: self.template_store.format(
                    templates.Templates.BOT_SEQUENCE_PREFIX,
                    {},
                ),
                templates.TemplateToken.BOT_SEQUENCE_SUFFIX: self.template_store.format(
                    templates.Templates.BOT_SEQUENCE_SUFFIX,
                    {},
                ),
                templates.TemplateToken.AI_NAME: self.persona.ai_name,
            },
        ).strip()

        # this will be also used when sending message
        # to suppress sending the prompt text to the user
        self.bot_name = self.template_store.format(
            templates.Templates.BOT_NAME,
            {
                templates.TemplateToken.NAME: self.persona.ai_name,
            },
        )
        self.bot_prompt_block = self.template_store.format(
            templates.Templates.BOT_PROMPT_HISTORY_BLOCK,
            {
                templates.TemplateToken.BOT_NAME: self.bot_name,
                templates.TemplateToken.MESSAGE: "",
            },
        )

        image_request_template_tokens = {
            templates.TemplateToken.AI_NAME: self.persona.ai_name,
            templates.TemplateToken.SYSTEM_SEQUENCE_PREFIX: self.template_store.format(
                templates.Templates.SYSTEM_SEQUENCE_PREFIX, {}
            ),
            templates.TemplateToken.SYSTEM_SEQUENCE_SUFFIX: self.template_store.format(
                templates.Templates.SYSTEM_SEQUENCE_SUFFIX, {}
            ),
            templates.TemplateToken.USER_SEQUENCE_PREFIX: self.template_store.format(
                templates.Templates.USER_SEQUENCE_PREFIX, {}
            ),
            templates.TemplateToken.USER_SEQUENCE_SUFFIX: self.template_store.format(
                templates.Templates.USER_SEQUENCE_SUFFIX, {}
            ),
            templates.TemplateToken.BOT_SEQUENCE_PREFIX: self.template_store.format(
                templates.Templates.BOT_SEQUENCE_PREFIX, {}
            ),
            templates.TemplateToken.BOT_SEQUENCE_SUFFIX: self.template_store.format(
                templates.Templates.BOT_SEQUENCE_SUFFIX, {}
            ),
        }
        self.image_request_made = self.template_store.format(
            templates.Templates.PROMPT_IMAGE_COMING,
            image_request_template_tokens
        )
        self.image_request_made = (self.image_request_made, len(self.image_request_made))

        self.image_request_failed = self.template_store.format(
            templates.Templates.PROMPT_IMAGE_NOT_COMING,
            image_request_template_tokens
        )
        self.image_request_failed = (self.image_request_failed, len(self.image_request_failed))

        if self.ooba_client.can_get_token_count():
            self.max_context_units = self.token_space - \
                oobabooga_settings["request_params"]["max_tokens"]
        else:
            self._init_history_available_chars()


    def _init_history_available_chars(self) -> None:
        """
        Calculate the number of characters we have available
        for history, and raise an exception if we don't have
        enough.

        Raises:
            ValueError: if we don't estimate to have enough space
                for the requested number of lines of history
        """
        # the number of chars we have available for history
        # is:
        #   number of chars in token space (estimated)
        #   minus the number of chars in the prompt
        #     - without any history
        #     - but with the image request
        #     - or the image failure notification, depending on which is bigger
        #
        est_chars_in_token_space = self.token_space * self.EST_CHARACTERS_PER_TOKEN
        prompt_without_history = self._generate(
            "",
            (
                self.image_request_made[0] if self.image_request_made[1]
                > self.image_request_failed[1] else self.image_request_failed[0]
            ),
            guild_name="",
            response_channel=""
        )

        # how many chars might we have available for history?
        available_chars_for_history = est_chars_in_token_space - len(
            prompt_without_history
        )
        # how many chars do we need for the requested number of
        # lines of history?
        chars_per_history_line = self.EST_CHARACTERS_PER_HISTORY_LINE
        if self.dont_split_responses:
            chars_per_history_line = (
                self.EST_CHARACTERS_PER_HISTORY_LINE_NOT_SPLITTING_RESPONSES
            )

        required_history_size_chars = self.history_lines * chars_per_history_line

        if available_chars_for_history < required_history_size_chars:
            fancy_logger.get().warning(
                "AI token space is too small for prompt_prefix and history "
                + "by an estimated %d"
                + " characters.  You may lose history context.  You can save space"
                + " by shortening the persona or reducing the requested number of"
                + " lines of history.",
                required_history_size_chars - available_chars_for_history,
            )
        self.max_context_units = available_chars_for_history

    def get_datetime(self) -> str:
        datetime_format = self.template_store.format(
            templates.Templates.DATETIME_FORMAT,
            {},
        )
        if os.environ.get("TZ"):
            tz=ZoneInfo(os.environ.get("TZ")) # type: ignore
        else:
            tz=None
        return datetime.now(tz=tz).strftime(datetime_format)

    async def _render_history(
        self,
        bot_user_id: int,
        message_history: typing.AsyncIterator[types.GenericMessage],
    ) -> str:
        # add on more history, but only if we have room
        # if we don't have room, we'll just truncate the history
        # by discarding the oldest messages first

        # history_lines is newest first, so figure out
        # how many we can take, then append them in
        # reverse order
        history_lines = []

        section_separator = self.template_store.format(
            templates.Templates.SECTION_SEPARATOR,
            {
                templates.TemplateToken.AI_NAME: self.persona.ai_name,
            },
        )
        prompt_without_history = self._generate(
            "",
            (
                self.image_request_made[0] if self.image_request_made[1]
                > self.image_request_failed[1] else self.image_request_failed[0]
            ),
            guild_name="",
            response_channel=""
        )
        #try:
        #    prompt_units = await self.ooba_client.get_token_count(prompt_without_history)
        #except ValueError:
        prompt_units = len(prompt_without_history)

        # first we process and append the chat transcript
        context_full = False
        async for message in message_history:
            if not message.body_text:
                continue

            if message.author_is_bot and message.author_id is bot_user_id:
                line = self.template_store.format(
                    templates.Templates.BOT_SEQUENCE_PREFIX,
                    {},
                )
                line += self.template_store.format(
                    templates.Templates.BOT_PROMPT_HISTORY_BLOCK,
                    {
                        templates.TemplateToken.BOT_NAME: self.bot_name,
                        templates.TemplateToken.MESSAGE: message.body_text,
                    },
                )
                line += self.template_store.format(
                    templates.Templates.BOT_SEQUENCE_SUFFIX,
                    {},
                )
            else:
                line = self.template_store.format(
                    templates.Templates.USER_SEQUENCE_PREFIX,
                    {},
                )
                line += self.template_store.format(
                    templates.Templates.USER_PROMPT_HISTORY_BLOCK,
                    {
                        templates.TemplateToken.USER_NAME: self.template_store.format(
                            templates.Templates.USER_NAME,
                            {
                                templates.TemplateToken.NAME: message.author_name,
                            },
                        ),
                        templates.TemplateToken.MESSAGE: message.body_text,
                    },
                )
                line += self.template_store.format(
                    templates.Templates.USER_SEQUENCE_SUFFIX,
                    {},
                )

            #try:
            #    line_units = await self.ooba_client.get_token_count(line)
            #except ValueError:
            line_units = len(line)

            if line_units >= self.max_context_units - prompt_units:
                context_full = True
                num_discarded_lines = self.history_lines - len(history_lines)
                fancy_logger.get().warning(
                    "Ran out of context space, discarding %d lines of chat history.",
                    num_discarded_lines,
                )
                break

            prompt_units += line_units
            history_lines.append(line)

        # then we append the example dialogue, if it exists, and there's room in the message history
        if len(self.example_dialogue) > 0:
            if not context_full:
                try:
                    separator_units = await self.ooba_client.get_token_count(section_separator)
                except ValueError:
                    separator_units = len(section_separator)
                context_full = prompt_units + separator_units >= self.max_context_units

            if not context_full:
                prompt_units += separator_units
                remaining_lines = self.history_lines - len(history_lines)

                if remaining_lines > 0:
                    # append the section separator (and newline) to the top which becomes the bottom
                    history_lines.append(section_separator + "\n")
                    # split example dialogue into lines and keep the newlines by rebuilding the list
                    # in a list comprehension
                    example_dialogue_lines = [
                        line + "\n" for line in self.example_dialogue.split("\n")]

                    # fill remaining quota of history lines with example dialogue lines
                    # this has the effect of gradually pushing them out as the chat exceeds
                    # the history limit
                    for _ in range(remaining_lines):
                        # start from the end of the list since the order is reversed
                        example_line = example_dialogue_lines.pop()
                        try:
                            example_units = await self.ooba_client.get_token_count(example_line)
                        except ValueError:
                            example_units = len(example_line)
                        if prompt_units + example_units > self.max_context_units:
                            break

                        prompt_units += example_units
                        # pop the last item of the list into the transcript
                        history_lines.append(example_line)
                        # and then break out of the loop once we run out of example dialogue
                        if not example_dialogue_lines:
                            break

        fancy_logger.get().debug(
            "Number of history lines: %d.",
            len(history_lines),
        )
        if self.ooba_client.can_get_token_count():
            unit_type = "tokens"
        else:
            unit_type = "characters"
        fancy_logger.get().debug(
            f"Total {unit_type} in prompt: %d. Max {unit_type} allowed: %d. Headroom: %d",
            prompt_units,
            self.max_context_units,
            self.max_context_units - prompt_units,
        )

        # then reverse the order of the list so it's in order again
        history_lines.reverse()
        if not self.reply_in_thread:
            # strip the last newline (moved to if statement due to causing errors when
            # 'reply in thread' is True?)
            history_lines[-1] = history_lines[-1].strip("\n")
        return "".join(history_lines)

    def _generate(
        self,
        message_history_txt: str,
        image_coming: str,
        guild_name: str,
        response_channel: str,
    ) -> str:
        current_datetime = self.get_datetime()
        prompt = self.template_store.format(
            templates.Templates.PROMPT,
            {
                templates.TemplateToken.AI_NAME: self.persona.ai_name,
                templates.TemplateToken.PERSONA: self.persona.persona,
                templates.TemplateToken.MESSAGE_HISTORY: message_history_txt,
                templates.TemplateToken.SECTION_SEPARATOR: self.template_store.format(
                    templates.Templates.SECTION_SEPARATOR,
                    {
                        templates.TemplateToken.AI_NAME: self.persona.ai_name,
                        templates.TemplateToken.CURRENTDATETIME: current_datetime,
                    },
                ),
                templates.TemplateToken.SYSTEM_SEQUENCE_PREFIX: self.template_store.format(
                    templates.Templates.SYSTEM_SEQUENCE_PREFIX,
                    {},
                ),
                templates.TemplateToken.SYSTEM_SEQUENCE_SUFFIX: self.template_store.format(
                    templates.Templates.SYSTEM_SEQUENCE_SUFFIX,
                    {},
                ),
                templates.TemplateToken.IMAGE_COMING: image_coming,
                templates.TemplateToken.GUILDNAME: guild_name,
                templates.TemplateToken.CHANNELNAME: response_channel,
                templates.TemplateToken.CURRENTDATETIME: current_datetime,
            },
        )
        prompt += self.template_store.format(
            templates.Templates.BOT_SEQUENCE_PREFIX,
            {},
        )
        prompt += self.bot_prompt_block
        return prompt

    async def generate(
        self,
        message_history: typing.Optional[typing.AsyncIterator[types.GenericMessage]],
        image_requested: typing.Optional[bool],
        bot_user_id: int,
        guild_name: str,
        response_channel: str,
    ) -> str:
        """
        Generate a prompt for the AI to respond to.
        """
        message_history_txt = ""
        if message_history:
            message_history_txt = await self._render_history(
                bot_user_id,
                message_history,
            )
        if image_requested:
            # True if image requested and SD is online
            image_coming = self.image_request_made[0]
        elif image_requested is False:
            # False if SD is offline and we can't
            image_coming = self.image_request_failed[0]
        else:
            # None if no image was requested
            image_coming = ""
        return self._generate(message_history_txt, image_coming, guild_name, response_channel)
