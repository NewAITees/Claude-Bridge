"""
Discord UI Components for Claude Bridge

Interactive UI components that convert Claude Code prompts to Discord buttons, menus, and modals.
"""

import asyncio
import re
from typing import List, Dict, Optional, Callable, Any, Tuple
from enum import Enum
import discord
from discord.ext import commands

from ..utils.logging_setup import get_logger

logger = get_logger('ui_components')


class InteractionType(Enum):
    """Types of interactive prompts"""
    YES_NO = "yes_no"
    CHOICE = "choice"
    TEXT_INPUT = "text_input"
    FILE_SELECTION = "file_selection"
    CONFIRMATION = "confirmation"
    MULTI_SELECT = "multi_select"


class PromptDetector:
    """Detects interactive prompts in Claude Code output"""
    
    # Patterns for different types of prompts
    PATTERNS = {
        InteractionType.YES_NO: [
            re.compile(r'(.*?)\s*\(y/n\)', re.IGNORECASE),
            re.compile(r'(.*?)\s*\(yes/no\)', re.IGNORECASE),
            re.compile(r'Do you want to\s+(.*?)\?', re.IGNORECASE),
            re.compile(r'Would you like to\s+(.*?)\?', re.IGNORECASE),
            re.compile(r'Continue\s+.*?\?', re.IGNORECASE),
            re.compile(r'Proceed\s+.*?\?', re.IGNORECASE),
        ],
        
        InteractionType.CHOICE: [
            re.compile(r'Select an option:\s*\n((?:\d+[.)]\s+.*\n?)+)', re.MULTILINE),
            re.compile(r'Choose from:\s*\n((?:[a-zA-Z][.)]\s+.*\n?)+)', re.MULTILINE),
            re.compile(r'Pick one:\s*\n((?:\*\s+.*\n?)+)', re.MULTILINE),
            re.compile(r'Options:\s*\n((?:\d+[.)]\s+.*\n?)+)', re.MULTILINE),
        ],
        
        InteractionType.TEXT_INPUT: [
            re.compile(r'Enter\s+(.*?):', re.IGNORECASE),
            re.compile(r'Input\s+(.*?):', re.IGNORECASE),
            re.compile(r'Type\s+(.*?):', re.IGNORECASE),
            re.compile(r'Provide\s+(.*?):', re.IGNORECASE),
            re.compile(r'What\s+.*\s+(.*?)\?', re.IGNORECASE),
        ],
        
        InteractionType.FILE_SELECTION: [
            re.compile(r'Select\s+a?\s*files?\s*:', re.IGNORECASE),
            re.compile(r'Choose\s+files?\s*:', re.IGNORECASE),
            re.compile(r'Pick\s+files?\s*from:', re.IGNORECASE),
            re.compile(r'Which\s+files?\s*:', re.IGNORECASE),
        ],
        
        InteractionType.CONFIRMATION: [
            re.compile(r'Are you sure.*?', re.IGNORECASE),
            re.compile(r'Confirm.*?', re.IGNORECASE),
            re.compile(r'This will.*continue\?', re.IGNORECASE),
            re.compile(r'This action.*proceed\?', re.IGNORECASE),
        ]
    }
    
    @classmethod
    def detect_prompt(cls, text: str) -> Optional[Tuple[InteractionType, Dict]]:
        """Detect if text contains an interactive prompt"""
        if not text or not text.strip():
            return None
            
        for interaction_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return interaction_type, cls._extract_prompt_info(text, match, interaction_type)
        
        return None
    
    @classmethod
    def _extract_prompt_info(cls, text: str, match: re.Match, interaction_type: InteractionType) -> Dict:
        """Extract information from the matched prompt"""
        info = {
            'full_text': text,
            'matched_text': match.group(),
            'prompt': match.group(1) if len(match.groups()) > 0 else text,
            'type': interaction_type
        }
        
        if interaction_type == InteractionType.CHOICE:
            info['options'] = cls._extract_options(text)
        elif interaction_type == InteractionType.TEXT_INPUT:
            info['field_name'] = match.group(1) if len(match.groups()) > 0 else "input"
        
        return info
    
    @classmethod
    def _extract_options(cls, text: str) -> List[str]:
        """Extract options from choice prompts"""
        options = []
        
        # Try different option formats
        patterns = [
            re.compile(r'^\s*(\d+)[.)]\s+(.*)$', re.MULTILINE),
            re.compile(r'^\s*([a-zA-Z])[.)]\s+(.*)$', re.MULTILINE),
            re.compile(r'^\s*\*\s+(.*)$', re.MULTILINE),
            re.compile(r'^\s*-\s+(.*)$', re.MULTILINE),
        ]
        
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                if isinstance(matches[0], tuple):
                    options = [match[1].strip() for match in matches]
                else:
                    options = [match.strip() for match in matches]
                break
        
        return options[:25]  # Discord limit for select menu


class ConfirmationView(discord.ui.View):
    """Yes/No confirmation view"""
    
    def __init__(self, prompt: str, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.result: Optional[bool] = None
        self.responded = asyncio.Event()
    
    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green, emoji='✅')
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle yes button click"""
        self.result = True
        self.responded.set()
        
        embed = discord.Embed(
            title="✅ Confirmed",
            description=f"You selected: **Yes**\n\n*{self.prompt}*",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label='No', style=discord.ButtonStyle.red, emoji='❌')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle no button click"""
        self.result = False
        self.responded.set()
        
        embed = discord.Embed(
            title="❌ Cancelled",
            description=f"You selected: **No**\n\n*{self.prompt}*",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        embed = discord.Embed(
            title="⏱️ Timed Out",
            description="No response received within the time limit.",
            color=discord.Color.orange()
        )
        
        # Try to edit the message if possible
        try:
            if hasattr(self, 'message') and self.message:
                await self.message.edit(embed=embed, view=None)
        except:
            pass


class ChoiceView(discord.ui.View):
    """Multiple choice selection view"""
    
    def __init__(self, prompt: str, options: List[str], timeout: float = 300):
        super().__init__(timeout=timeout)
        self.prompt = prompt
        self.options = options[:25]  # Discord limit
        self.result: Optional[str] = None
        self.responded = asyncio.Event()
        
        # Add select menu
        self.add_item(ChoiceSelect(options, self.on_select))
    
    async def on_select(self, selection: str):
        """Handle selection"""
        self.result = selection
        self.responded.set()


class ChoiceSelect(discord.ui.Select):
    """Select menu for choices"""
    
    def __init__(self, options: List[str], callback_func: Callable):
        self.callback_func = callback_func
        
        # Create options (max 25)
        select_options = []
        for i, option in enumerate(options[:25]):
            # Truncate long options
            label = option[:100] if len(option) > 100 else option
            description = option[100:200] + "..." if len(option) > 200 else None
            
            select_options.append(discord.SelectOption(
                label=label,
                value=str(i),
                description=description
            ))
        
        super().__init__(
            placeholder="Choose an option...",
            min_values=1,
            max_values=1,
            options=select_options
        )
        
        self.option_texts = options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle select callback"""
        selected_index = int(self.values[0])
        selected_option = self.option_texts[selected_index]
        
        embed = discord.Embed(
            title="✅ Selected",
            description=f"You selected: **{selected_option}**",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        await self.callback_func(selected_option)


class TextInputModal(discord.ui.Modal):
    """Modal for text input"""
    
    def __init__(self, prompt: str, field_name: str = "input", timeout: float = 300):
        super().__init__(title="Input Required", timeout=timeout)
        self.prompt = prompt
        self.result: Optional[str] = None
        self.responded = asyncio.Event()
        
        # Create text input
        self.text_input = discord.ui.TextInput(
            label=field_name,
            placeholder=prompt,
            style=discord.TextStyle.paragraph if len(prompt) > 50 else discord.TextStyle.short,
            max_length=2000,
            required=True
        )
        
        self.add_item(self.text_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        self.result = self.text_input.value
        self.responded.set()
        
        embed = discord.Embed(
            title="✅ Input Received",
            description=f"You entered:\n```\n{self.text_input.value}\n```",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


class UIConverter:
    """Converts Claude Code prompts to Discord UI components"""
    
    def __init__(self):
        self.pending_interactions: Dict[str, Any] = {}
    
    async def handle_prompt(self, text: str, channel: discord.TextChannel, 
                          session_id: str) -> Optional[str]:
        """
        Handle an interactive prompt by converting it to Discord UI
        Returns the user's response or None if not an interactive prompt
        """
        
        # Detect prompt type
        detection = PromptDetector.detect_prompt(text)
        if not detection:
            return None
        
        interaction_type, prompt_info = detection
        logger.info(f"Detected {interaction_type.value} prompt for session {session_id}")
        
        try:
            if interaction_type in [InteractionType.YES_NO, InteractionType.CONFIRMATION]:
                return await self._handle_yes_no(prompt_info, channel, session_id)
            
            elif interaction_type == InteractionType.CHOICE:
                return await self._handle_choice(prompt_info, channel, session_id)
            
            elif interaction_type == InteractionType.TEXT_INPUT:
                return await self._handle_text_input(prompt_info, channel, session_id)
            
            else:
                # Fallback to simple text prompt
                return await self._handle_text_prompt(prompt_info, channel, session_id)
                
        except Exception as e:
            logger.error(f"Error handling prompt: {e}")
            return None
    
    async def _handle_yes_no(self, prompt_info: Dict, channel: discord.TextChannel, 
                           session_id: str) -> Optional[str]:
        """Handle yes/no prompts"""
        
        embed = discord.Embed(
            title="🤔 Confirmation Required",
            description=prompt_info['prompt'],
            color=discord.Color.blue()
        )
        
        view = ConfirmationView(prompt_info['prompt'])
        message = await channel.send(embed=embed, view=view)
        view.message = message
        
        # Store pending interaction
        self.pending_interactions[session_id] = view
        
        # Wait for response
        try:
            await asyncio.wait_for(view.responded.wait(), timeout=300)
            return "yes" if view.result else "no"
        except asyncio.TimeoutError:
            logger.warning(f"Yes/No prompt timed out for session {session_id}")
            return None
        finally:
            self.pending_interactions.pop(session_id, None)
    
    async def _handle_choice(self, prompt_info: Dict, channel: discord.TextChannel,
                           session_id: str) -> Optional[str]:
        """Handle multiple choice prompts"""
        
        options = prompt_info.get('options', [])
        if not options:
            logger.warning("No options found in choice prompt")
            return None
        
        embed = discord.Embed(
            title="📝 Please Select",
            description=prompt_info['prompt'],
            color=discord.Color.blue()
        )
        
        # Add options to embed
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        embed.add_field(name="Options", value=options_text, inline=False)
        
        view = ChoiceView(prompt_info['prompt'], options)
        message = await channel.send(embed=embed, view=view)
        view.message = message
        
        # Store pending interaction
        self.pending_interactions[session_id] = view
        
        # Wait for response
        try:
            await asyncio.wait_for(view.responded.wait(), timeout=300)
            # Return the index + 1 (as Claude Code expects 1-based indexing)
            if view.result:
                option_index = options.index(view.result) + 1
                return str(option_index)
            return None
        except asyncio.TimeoutError:
            logger.warning(f"Choice prompt timed out for session {session_id}")
            return None
        finally:
            self.pending_interactions.pop(session_id, None)
    
    async def _handle_text_input(self, prompt_info: Dict, channel: discord.TextChannel,
                                session_id: str) -> Optional[str]:
        """Handle text input prompts"""
        
        embed = discord.Embed(
            title="✏️ Input Required",
            description=prompt_info['prompt'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Instructions",
            value="Click the button below to open the input form.",
            inline=False
        )
        
        # Create a button to open the modal
        class ModalButton(discord.ui.View):
            def __init__(self, prompt: str, field_name: str):
                super().__init__(timeout=300)
                self.prompt = prompt
                self.field_name = field_name
                self.result: Optional[str] = None
                self.responded = asyncio.Event()
            
            @discord.ui.button(label='Open Input Form', style=discord.ButtonStyle.primary, emoji='✏️')
            async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = TextInputModal(self.prompt, self.field_name)
                await interaction.response.send_modal(modal)
                
                # Wait for modal completion
                await modal.responded.wait()
                self.result = modal.result
                self.responded.set()
        
        field_name = prompt_info.get('field_name', 'input')
        view = ModalButton(prompt_info['prompt'], field_name)
        message = await channel.send(embed=embed, view=view)
        
        # Store pending interaction
        self.pending_interactions[session_id] = view
        
        # Wait for response
        try:
            await asyncio.wait_for(view.responded.wait(), timeout=300)
            return view.result
        except asyncio.TimeoutError:
            logger.warning(f"Text input prompt timed out for session {session_id}")
            return None
        finally:
            self.pending_interactions.pop(session_id, None)
    
    async def _handle_text_prompt(self, prompt_info: Dict, channel: discord.TextChannel,
                                 session_id: str) -> Optional[str]:
        """Handle generic text prompts with message waiting"""
        
        embed = discord.Embed(
            title="💬 Response Required",
            description=prompt_info['prompt'],
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Instructions",
            value="Please type your response in the chat.",
            inline=False
        )
        
        await channel.send(embed=embed)
        
        # Wait for next message from user
        def check(message):
            return (message.channel == channel and 
                   not message.author.bot and
                   message.content.strip())
        
        try:
            bot = channel.guild.get_member_named(channel.guild.me.name)  # Get bot reference
            message = await bot.wait_for('message', check=check, timeout=300)
            return message.content
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏱️ Timed Out",
                description="No response received within the time limit.",
                color=discord.Color.orange()
            )
            await channel.send(embed=timeout_embed)
            return None
    
    def cancel_pending_interaction(self, session_id: str):
        """Cancel any pending interaction for a session"""
        if session_id in self.pending_interactions:
            interaction = self.pending_interactions.pop(session_id)
            if hasattr(interaction, 'responded'):
                interaction.responded.set()
            logger.info(f"Cancelled pending interaction for session {session_id}")
    
    def get_pending_interactions(self) -> List[str]:
        """Get list of sessions with pending interactions"""
        return list(self.pending_interactions.keys())