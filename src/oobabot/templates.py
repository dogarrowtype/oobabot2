# -*- coding: utf-8 -*-
"""
Templates for text generated by the bot. There are two types:
 - templates used to generate prompts for the AI
 - templates used to generate UI messages for the user
 Both types may or may not contain template tokens that are
 substituted for the relevant contents at runtime.
"""

import enum
import functools
import textwrap
import typing


@functools.total_ordering
class Templates(enum.Enum):
    """
    Enumeration of all different templates.
    """

    COMMAND_ACKNOWLEDGEMENT = "command_acknowledgement"
    COMMAND_LOBOTOMIZE_RESPONSE = "command_lobotomize_response"

    IMAGE_DETACH = "image_detach"
    IMAGE_CONFIRMATION = "image_confirmation"
    IMAGE_GENERATION_ERROR = "image_generation_error"
    IMAGE_UNAUTHORIZED = "image_unauthorized"

    # prompts to the AI to generate text responses
    PROMPT = "prompt"
    EXAMPLE_DIALOGUE = "example_dialogue"
    SECTION_SEPARATOR = "section_separator"
    DATETIME_FORMAT = "datetime_format"
    SYSTEM_SEQUENCE_PREFIX = "system_sequence_prefix"
    SYSTEM_SEQUENCE_SUFFIX = "system_sequence_suffix"
    USER_SEQUENCE_PREFIX = "user_sequence_prefix"
    USER_SEQUENCE_SUFFIX = "user_sequence_suffix"
    BOT_SEQUENCE_PREFIX = "bot_sequence_prefix"
    BOT_SEQUENCE_SUFFIX = "bot_sequence_suffix"
    USER_PROMPT_HISTORY_BLOCK = "user_prompt_history_block"
    BOT_PROMPT_HISTORY_BLOCK = "bot_prompt_history_block"
    VISION_SYSTEM_PROMPT = "vision_system_prompt"
    VISION_PROMPT = "vision_prompt"
    PROMPT_IMAGE_RECEIVED = "prompt_image_received"
    PROMPT_IMAGE_COMING = "prompt_image_coming"
    PROMPT_IMAGE_NOT_COMING = "prompt_image_not_coming"
    PROMPT_IMAGE_SENT = "prompt_image_sent"

    def __str__(self) -> str:
        return self.value

    def __lt__(self, other: "Templates") -> bool:
        return str(self.value) < str(other.value)


class TemplateToken(str, enum.Enum):
    """
    Enumeration of all tokens used in templates.
    Tokens are variable substitutions into the templates.
    """

    AI_NAME = "AI_NAME"
    DESCRIPTION = "DESCRIPTION"
    PERSONALITY = "PERSONALITY"
    SCENARIO = "SCENARIO"
    BOT_DISPLAY_NAME = "BOT_DISPLAY_NAME"
    USER_NAME = "USER_NAME"
    GUILD_NAME = "GUILD_NAME"
    CHANNEL_NAME = "CHANNEL_NAME"
    CURRENT_DATETIME = "CURRENT_DATETIME"
    IMAGE_PROMPT = "IMAGE_PROMPT"
    IMAGE_TIMEOUT = "IMAGE_TIMEOUT"
    SECTION_SEPARATOR = "SECTION_SEPARATOR"
    EXAMPLE_DIALOGUE = "EXAMPLE_DIALOGUE"
    MESSAGE_HISTORY = "MESSAGE_HISTORY"
    SYSTEM_MESSAGE = "SYSTEM_MESSAGE"
    NAME = "NAME"
    SYSTEM_SEQUENCE_PREFIX = "SYSTEM_SEQUENCE_PREFIX"
    SYSTEM_SEQUENCE_SUFFIX = "SYSTEM_SEQUENCE_SUFFIX"
    USER_SEQUENCE_PREFIX = "USER_SEQUENCE_PREFIX"
    USER_SEQUENCE_SUFFIX = "USER_SEQUENCE_SUFFIX"
    BOT_SEQUENCE_PREFIX = "BOT_SEQUENCE_PREFIX"
    BOT_SEQUENCE_SUFFIX = "BOT_SEQUENCE_SUFFIX"
    MESSAGE = "MESSAGE"

    def __str__(self):
        return "{" + self.value + "}"


class TemplateStore:
    """
    Data object storing all template definitions and default values.
    """

    # mapping of template names to tokens allowed in that template
    #  key: template name
    #  value: tuple of (list of tokens, description, is_an_ai_prompt)
    TEMPLATES: typing.Dict[
        Templates, typing.Tuple[typing.List[TemplateToken], str]
    ] = {
        Templates.SYSTEM_SEQUENCE_PREFIX: (
            [],
            "The sequence that should be inserted before system messages."
        ),
        Templates.SYSTEM_SEQUENCE_SUFFIX: (
            [],
            "The sequence that should be inserted after system messages. "
            + "By default, this is just a single newline. Make sure this "
            + "ends with a newline if messages are meant to be separated "
            + "by them!"
        ),
        Templates.USER_SEQUENCE_PREFIX: (
            [],
            "The sequence that should be inserted before user messages."
        ),
        Templates.USER_SEQUENCE_SUFFIX: (
            [],
            "The sequence that should be inserted after user messages. "
            + "By default, this is just a single newline. Make sure this "
            + "ends with a newline if messages are meant to be separated "
            + "by them!"
        ),
        Templates.BOT_SEQUENCE_PREFIX: (
            [],
            "The sequence that should be inserted before bot messages."
        ),
        Templates.BOT_SEQUENCE_SUFFIX: (
            [],
            "The sequence that should be inserted after bot messages. "
            + "By default, this is just a single newline. Make sure this "
            + "ends with a newline if messages are meant to be separated "
            + "by them!"
        ),
        Templates.USER_PROMPT_HISTORY_BLOCK: (
            [
                TemplateToken.NAME,
                TemplateToken.MESSAGE
            ],
            "Part of the AI response-generation prompt, this is used to "
            + "render user messages in the chat history. A list of these, "
            + "one for each past user message, will become part of "
            + "{MESSAGE_HISTORY} and inserted into the main prompt."
        ),
        Templates.BOT_PROMPT_HISTORY_BLOCK: (
            [
                TemplateToken.NAME,
                TemplateToken.MESSAGE
            ],
            "Part of the AI response-generation prompt, this is used to "
            + "render bot messages in the chat history. A list of these, "
            + "one for each past bot message, will become part of "
            + "{MESSAGE_HISTORY} and inserted into the main prompt."
        ),
        Templates.PROMPT: (
            [
                TemplateToken.SYSTEM_SEQUENCE_PREFIX,
                TemplateToken.SYSTEM_SEQUENCE_SUFFIX,
                TemplateToken.AI_NAME,
                TemplateToken.DESCRIPTION,
                TemplateToken.PERSONALITY,
                TemplateToken.SCENARIO,
                TemplateToken.CHANNEL_NAME,
                TemplateToken.GUILD_NAME,
                TemplateToken.CURRENT_DATETIME,
                TemplateToken.SECTION_SEPARATOR,
                TemplateToken.MESSAGE_HISTORY,
                TemplateToken.SYSTEM_MESSAGE
            ],
            "The main prompt sent to the text generation API to generate a "
            + "response from the AI. The AI's reply to this prompt will be "
            + "sent to Discord as the bot's response."
        ),
        Templates.SECTION_SEPARATOR: (
            [
                TemplateToken.SYSTEM_SEQUENCE_PREFIX,
                TemplateToken.SYSTEM_SEQUENCE_SUFFIX,
                TemplateToken.AI_NAME
            ],
            "Separator between different sections, if necessary. For example, to "
            + "separate example dialogue from the main chat transcript. Ensure "
            + "that this ends with a newline, if messages are meant to be "
            + "separated by them."
        ),
        Templates.EXAMPLE_DIALOGUE: (
            [
                TemplateToken.SYSTEM_SEQUENCE_PREFIX,
                TemplateToken.SYSTEM_SEQUENCE_SUFFIX,
                TemplateToken.USER_SEQUENCE_PREFIX,
                TemplateToken.USER_SEQUENCE_SUFFIX,
                TemplateToken.BOT_SEQUENCE_PREFIX,
                TemplateToken.BOT_SEQUENCE_SUFFIX,
                TemplateToken.AI_NAME
            ],
            "A section separator and this example dialogue inserted directly before "
            + "the message history, with the section separator coming first. This is "
            + "gradually pushed out as the chat grows beyond the context length in the "
            + "same way as as the message history itself."
        ),
        Templates.DATETIME_FORMAT: (
            [],
            "strftime-formatted string to render current timestamp."
        ),
        Templates.VISION_SYSTEM_PROMPT: (
            [
                TemplateToken.AI_NAME
            ],
            "This is the system prompt sent to the Vision model. If this is set to an "
            + "empty string (i.e. \"\"), the system prompt is ignored. Useful for some "
            + "Vision APIs that do not support system prompts.",
        ),
        Templates.VISION_PROMPT: (
            [],
            "The user instruction prompt sent to the Vision model."
        ),
        Templates.PROMPT_IMAGE_RECEIVED: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.USER_NAME
            ],
            "Part of the AI response-generation prompt, this is used to prefix "
            + "any image descriptions we get from the Vision API."
        ),
        Templates.PROMPT_IMAGE_COMING: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.USER_NAME,
                TemplateToken.SYSTEM_SEQUENCE_PREFIX,
                TemplateToken.SYSTEM_SEQUENCE_SUFFIX,
                TemplateToken.USER_SEQUENCE_PREFIX,
                TemplateToken.USER_SEQUENCE_SUFFIX,
                TemplateToken.BOT_SEQUENCE_PREFIX,
                TemplateToken.BOT_SEQUENCE_SUFFIX
            ],
            "Part of the AI response-generation prompt, this is used to inform "
            + "the AI that it is in the process of generating an image."
        ),
        Templates.PROMPT_IMAGE_NOT_COMING: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.USER_NAME,
                TemplateToken.SYSTEM_SEQUENCE_PREFIX,
                TemplateToken.SYSTEM_SEQUENCE_SUFFIX,
                TemplateToken.USER_SEQUENCE_PREFIX,
                TemplateToken.USER_SEQUENCE_SUFFIX,
                TemplateToken.BOT_SEQUENCE_PREFIX,
                TemplateToken.BOT_SEQUENCE_SUFFIX
            ],
            "Part of the AI response-generation prompt, this is used to inform "
            + "the AI that its image generator is offline and is not functioning."
        ),
        Templates.PROMPT_IMAGE_SENT: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.IMAGE_PROMPT
            ],
            "Part of the AI response-generation prompt, this is used to inform "
            + "the AI that it posted the generated image with the requested prompt."
        ),
        Templates.COMMAND_ACKNOWLEDGEMENT: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.NAME
            ],
            "Displayed in Discord for commands that warrant an acknowledgement. "
            + "Only the user issuing the command will see this, and it is ephemeral."
        ),
        Templates.COMMAND_LOBOTOMIZE_RESPONSE: (
            [
                TemplateToken.AI_NAME,
                TemplateToken.NAME
            ],
            "Displayed in Discord after a successful /lobotomize command. "
            + "Both the Discord users and the AI will see this message, "
            + "unless the bot is configured not to."
        ),
        Templates.IMAGE_CONFIRMATION: (
            [
                TemplateToken.NAME,
                TemplateToken.IMAGE_PROMPT,
                TemplateToken.IMAGE_TIMEOUT
            ],
            "Shown in Discord when an image is first generated from "
            + "Stable Diffusion. This should prompt the user to either "
            + "save or discard the image."
        ),
        Templates.IMAGE_DETACH: (
            [
                TemplateToken.NAME,
                TemplateToken.IMAGE_PROMPT
            ],
            "Shown in Discord when the user selects to discard an image "
            + "that Stable Diffusion had generated."
        ),
        Templates.IMAGE_UNAUTHORIZED: (
            [
                TemplateToken.NAME
            ],
            "Shown in Discord privately to a user if they try to regenerate "
            + "an image that was requested by someone else."
        ),
        Templates.IMAGE_GENERATION_ERROR: (
            [
                TemplateToken.NAME,
                TemplateToken.IMAGE_PROMPT
            ],
            "Shown in Discord when the we could not contact Stable Diffusion "
            + "to generate an image."
        )
    }

    DEFAULT_TEMPLATES: typing.Dict[Templates, str] = {
        Templates.SYSTEM_SEQUENCE_PREFIX: "",
        Templates.SYSTEM_SEQUENCE_SUFFIX: "\n",
        Templates.USER_SEQUENCE_PREFIX: "",
        Templates.USER_SEQUENCE_SUFFIX: "\n",
        Templates.BOT_SEQUENCE_PREFIX: "",
        Templates.BOT_SEQUENCE_SUFFIX: "\n",
        Templates.USER_PROMPT_HISTORY_BLOCK: "{NAME}: {MESSAGE}",
        Templates.BOT_PROMPT_HISTORY_BLOCK: "{NAME}: {MESSAGE}",
        Templates.PROMPT: textwrap.dedent(
            """
            You are in a Discord guild called {GUILD_NAME}, in a chat room called
            {CHANNEL_NAME} with multiple participants. Below is a transcript of
            recent messages in the conversation. Write the next one to three
            messages that you would send in this conversation, from the point of
            view of the participant named {AI_NAME}.
            """
        ) + "\n\n" +
        textwrap.dedent(
            """
            {DESCRIPTION}
            {AI_NAME}'s personality: {PERSONALITY}
            Scenario: {SCENARIO}

            All responses you write must be from the point of view of {AI_NAME}.
            ### Transcript:
            {MESSAGE_HISTORY}
            {SYSTEM_MESSAGE}
            """
        ),
        Templates.SECTION_SEPARATOR: "***",
        Templates.EXAMPLE_DIALOGUE: "",
        Templates.DATETIME_FORMAT: "%B %d, %Y - %I:%M:%S %p",
        Templates.VISION_SYSTEM_PROMPT: textwrap.dedent(
            """
            A chat between a curious human and an artificial intelligence assistant.
            The assistant gives helpful, detailed, and polite answers to the human's questions.
            """
        ),
        Templates.VISION_PROMPT: textwrap.dedent(
            """
            Describe the following image in as much detail as possible,
            including any relevant details while being concise.
            """
        ),
        Templates.PROMPT_IMAGE_RECEIVED: textwrap.dedent(
            """
            {USER_NAME} posted an image and your image recognition system describes it to you: 
            """
        ),
        Templates.PROMPT_IMAGE_COMING: textwrap.dedent(
            """
            {SYSTEM_SEQUENCE_PREFIX}{AI_NAME} is currently generating an image,
            as requested.{SYSTEM_SEQUENCE_SUFFIX}
            """
        ),
        Templates.PROMPT_IMAGE_NOT_COMING: textwrap.dedent(
            """
            {SYSTEM_SEQUENCE_PREFIX}{AI_NAME}'s image generator is offline or
            has failed for some reason!{SYSTEM_SEQUENCE_SUFFIX}
            """
        ),
        Templates.PROMPT_IMAGE_SENT: textwrap.dedent(
            """
            {AI_NAME} posts an image generated with the prompt: {IMAGE_PROMPT}
            """
        ),
        Templates.COMMAND_ACKNOWLEDGEMENT: "Okay.",
        Templates.COMMAND_LOBOTOMIZE_RESPONSE: "Ummmm... what were we talking about?",
        Templates.IMAGE_CONFIRMATION:
            "{NAME}, is this what you wanted?\n"
            + "If no choice is made, this message will 💣 self-destruct 💣 in 3 minutes.",
        Templates.IMAGE_DETACH:
            "{NAME} asked for an image with the prompt:\n"
            + "    '{IMAGE_PROMPT}'\n"
            + "...but couldn't find a suitable one.",
        Templates.IMAGE_GENERATION_ERROR: textwrap.dedent(
            """
            Something went wrong generating your image. Sorry about that!
            """
        ),
        Templates.IMAGE_UNAUTHORIZED: "Sorry, only {NAME} can press the buttons."
    }

    def __init__(self, settings: dict):
        self.templates: typing.Dict[Templates, TemplateMessageFormatter] = {}
        for template, (tokens, _purpose) in self.TEMPLATES.items():
            template_name = str(template)
            template_fmt = settings[template_name]
            if template_fmt is None:
                raise ValueError(f"Template {template_name} has no default format")
            self.add_template(template, template_fmt, tokens)

    def add_template(
        self,
        template_name: Templates,
        format_str: str,
        allowed_tokens: typing.List[TemplateToken]
    ):
        self.templates[template_name] = TemplateMessageFormatter(
            template_name,
            format_str,
            allowed_tokens
        )

    def format(
        self, template_name: Templates, format_args: typing.Dict[TemplateToken, str]
    ) -> str:
        """
        Format the template, substituting tokens with strings given by format_args.
        """
        return self.templates[template_name].format(format_args)

    def get(
        self, template_name: Templates
    ) -> str:
        """
        Returns the unformatted template string, before tokens are substituted.
        """
        return str(self.templates[template_name])


class TemplateMessageFormatter:
    """
    Validates that templates are safe to run string.format() on, and
    runs string.format()
    """

    def __init__(
        self,
        template_name: Templates,
        template: str,
        allowed_tokens: typing.List[TemplateToken]
    ):
        self._validate_format_string(template_name, template, allowed_tokens)
        self.template_name = template_name
        self.template = template
        self.allowed_tokens = allowed_tokens

    def __str__(self):
        return self.template

    def format(self, format_args: typing.Dict[TemplateToken, str]) -> str:
        return self.template.format(**format_args)

    @staticmethod
    def _validate_format_string(
        template_name: Templates,
        format_str: str,
        allowed_args: typing.List[TemplateToken],
    ):
        def find_all_ch(string: str, char: str) -> typing.Generator[int, None, None]:
            # find all indices of ch in s
            for i, letter in enumerate(string):
                if letter == char:
                    yield i

        # raises if fmt_string contains any args not in allowed_args
        allowed_close_brace_indices: typing.Set[int] = set()

        for open_brace_idx in find_all_ch(format_str, "{"):
            for allowed_arg in allowed_args:
                idx_end = open_brace_idx + len(allowed_arg) + 1
                next_substr = format_str[open_brace_idx : idx_end + 1]
                if next_substr == "{" + allowed_arg + "}":
                    allowed_close_brace_indices.add(idx_end)
                    break
            else:
                raise ValueError(
                    f"invalid template: {template_name} contains "
                    + f"an argument not in {allowed_args}"
                )
        for close_brace_idx in find_all_ch(format_str, "}"):
            if close_brace_idx not in allowed_close_brace_indices:
                raise ValueError(
                    f"invalid template: {template_name} contains "
                    + f"an argument not in {allowed_args}"
                )
