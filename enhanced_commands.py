import discord
from discord.ext import commands
import math

def setup_enhanced_commands(bot_instance, sniped_messages_dict, messages_per_page, detect_media_func, get_media_url_func, is_offensive_content_func, is_user_blocked_func):
    """Setup function to register commands with the bot instance"""
    
    # Store references to imported functions and variables
    global bot, sniped_messages, MESSAGES_PER_PAGE, detect_media_type, get_media_url, is_offensive_content, is_user_blocked
    bot = bot_instance
    sniped_messages = sniped_messages_dict
    MESSAGES_PER_PAGE = messages_per_page
    detect_media_type = detect_media_func
    get_media_url = get_media_url_func
    is_offensive_content = is_offensive_content_func
    is_user_blocked = is_user_blocked_func

    # Helper function to resolve channel/thread by name
    async def resolve_channel_or_thread(guild, channel_input):
        """Resolve channel or thread by name (supports #channelname syntax)"""
        if not channel_input:
            return None
        
        # Remove # if present
        channel_name = channel_input.lstrip('#').lower()
        
        # First check regular channels
        for channel in guild.text_channels:
            if channel.name.lower() == channel_name:
                return channel
        
        # Then check threads in all channels
        for channel in guild.text_channels:
            try:
                # Check active threads
                for thread in channel.threads:
                    if thread.name.lower() == channel_name:
                        return thread
                
                # Check archived threads
                async for thread in channel.archived_threads():
                    if thread.name.lower() == channel_name:
                        return thread
            except discord.Forbidden:
                continue
        
        return None

    # Command: ,spall (all deleted messages from all channels)
    @bot.command(name='spall', help='Show ALL deleted messages from all channels and threads')
    async def snipe_all_messages(ctx, page: int = 1):
        """Show ALL deleted messages from all channels and threads"""
        if is_user_blocked(ctx.author.id):
            return
        
        # Collect from all channels and threads
        all_messages = []
        
        for channel_id, messages in sniped_messages.items():
            channel_obj = bot.get_channel(channel_id)
            if channel_obj and channel_obj.guild == ctx.guild:
                for msg in messages:
                    msg_copy = msg.copy()
                    if isinstance(channel_obj, discord.Thread):
                        msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                    else:
                        msg_copy['source_info'] = f"#{channel_obj.name}"
                    all_messages.append(msg_copy)
        
        # Sort by timestamp
        all_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        if not all_messages:
            embed = discord.Embed(
                title="👻 No Deleted Messages",
                description="No deleted messages found in any channel.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Pagination
        total_pages = math.ceil(len(all_messages) / MESSAGES_PER_PAGE)
        page = max(1, min(page, total_pages))
        
        embed = discord.Embed(
            title="👻 Deleted Messages - All Channels",
            color=discord.Color.purple()
        )
        
        start_idx = (page - 1) * MESSAGES_PER_PAGE
        end_idx = start_idx + MESSAGES_PER_PAGE
        page_messages = all_messages[start_idx:end_idx]
        
        content_lines = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            author_name = msg['author'].display_name
            content = msg['content'] or "*No text content*"
            
            content_lines.append(f"**{i}. {author_name}**")
            content_lines.append(f"{content}")
            content_lines.append(f"📍 {msg['source_info']}")
            content_lines.append("")  # Empty line for spacing
        
        embed.description = "\n".join(content_lines)
        embed.set_footer(text=f"Page {page} of {total_pages} | {len(all_messages)} total messages")
        
        await ctx.send(embed=embed)

    # Command: ,splall (all deleted links from all channels or specific channel/thread)
    @bot.command(name='splall', help='Show deleted links from all channels or specific channel/thread')
    async def snipe_links_all(ctx, channel_input=None, page: int = 1):
        """Show deleted links from all channels or specific channel/thread"""
        if is_user_blocked(ctx.author.id):
            return
        
        if channel_input:
            # Show links from specific channel/thread
            target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Channel Not Found",
                    description=f"Could not find channel or thread: `{channel_input}`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            channel_id = target_channel.id
            if isinstance(target_channel, discord.Thread):
                location_text = f"#{target_channel.parent.name} → {target_channel.name}"
            else:
                location_text = f"#{target_channel.name}"
            
            if channel_id not in sniped_messages:
                embed = discord.Embed(
                    title="🔗 No Link Messages",
                    description=f"No deleted messages with links found in {location_text}.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
            
            # Filter messages with media/links from specific channel
            media_messages = []
            for msg in sniped_messages[channel_id]:
                has_media = False
                
                if msg.get('attachments'):
                    has_media = True
                
                if msg.get('content'):
                    media_urls = get_media_url(msg['content'], [])
                    if media_urls:
                        has_media = True
                
                if has_media:
                    media_messages.append(msg)
            
            title = f"🔗 Deleted Link Messages - {location_text}"
            show_source = False
            
        else:
            # Show links from ALL channels and threads
            media_messages = []
            
            for channel_id, messages in sniped_messages.items():
                channel_obj = bot.get_channel(channel_id)
                if channel_obj and channel_obj.guild == ctx.guild:
                    for msg in messages:
                        has_media = False
                        
                        if msg.get('attachments'):
                            has_media = True
                        
                        if msg.get('content'):
                            media_urls = get_media_url(msg['content'], [])
                            if media_urls:
                                has_media = True
                        
                        if has_media:
                            msg_copy = msg.copy()
                            if isinstance(channel_obj, discord.Thread):
                                msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                            else:
                                msg_copy['source_info'] = f"#{channel_obj.name}"
                            media_messages.append(msg_copy)
            
            title = "🔗 Deleted Link Messages - All Channels"
            show_source = True
        
        if not media_messages:
            embed = discord.Embed(
                title="🔗 No Link Messages",
                description="No deleted messages with links found.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by timestamp
        media_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Pagination
        total_pages = math.ceil(len(media_messages) / MESSAGES_PER_PAGE)
        page = max(1, min(page, total_pages))
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue()
        )
        
        start_idx = (page - 1) * MESSAGES_PER_PAGE
        end_idx = start_idx + MESSAGES_PER_PAGE
        page_messages = media_messages[start_idx:end_idx]
        
        content_lines = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            author_name = msg['author'].display_name
            content = msg['content'] or ""
            
            # Extract links
            links = []
            if msg.get('attachments'):
                for attachment in msg['attachments']:
                    links.append(attachment.url)
            
            if msg.get('content'):
                media_urls = get_media_url(msg['content'], [])
                if media_urls:
                    for media in media_urls:
                        if media.get('source') == 'embedded':
                            links.append(media['url'])
            
            content_lines.append(f"**{i}. {author_name}**")
            if content and content.strip():
                content_lines.append(content)
            
            for link in links:
                content_lines.append(link)
            
            if show_source and 'source_info' in msg:
                content_lines.append(f"📍 {msg['source_info']}")
            
            content_lines.append("")  # Empty line for spacing
        
        embed.description = "\n".join(content_lines)
        embed.set_footer(text=f"Page {page} of {total_pages} | {len(media_messages)} total messages")
        
        await ctx.send(embed=embed)

    # Command: ,spfall (all clean messages from all channels or specific channel/thread)
    @bot.command(name='spfall', help='Show clean messages from all channels or specific channel/thread')
    async def snipe_filtered_all(ctx, channel_input=None, page: int = 1):
        """Show clean messages from all channels or specific channel/thread"""
        if is_user_blocked(ctx.author.id):
            return
        
        if channel_input:
            # Show clean messages from specific channel/thread
            target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
            if not target_channel:
                embed = discord.Embed(
                    title="❌ Channel Not Found",
                    description=f"Could not find channel or thread: `{channel_input}`",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            channel_id = target_channel.id
            if isinstance(target_channel, discord.Thread):
                location_text = f"#{target_channel.parent.name} → {target_channel.name}"
            else:
                location_text = f"#{target_channel.name}"
            
            if channel_id not in sniped_messages:
                embed = discord.Embed(
                    title="✅ No Clean Messages",
                    description=f"No clean messages found in {location_text}.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
            
            # Filter clean messages from specific channel
            clean_messages = []
            for msg in sniped_messages[channel_id]:
                if not is_offensive_content(msg.get('content', '')):
                    clean_messages.append(msg)
            
            title = f"✅ Clean Messages - {location_text}"
            show_source = False
            
        else:
            # Show clean messages from ALL channels and threads
            clean_messages = []
            
            for channel_id, messages in sniped_messages.items():
                channel_obj = bot.get_channel(channel_id)
                if channel_obj and channel_obj.guild == ctx.guild:
                    for msg in messages:
                        if not is_offensive_content(msg.get('content', '')):
                            msg_copy = msg.copy()
                            if isinstance(channel_obj, discord.Thread):
                                msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                            else:
                                msg_copy['source_info'] = f"#{channel_obj.name}"
                            clean_messages.append(msg_copy)
            
            title = "✅ Clean Messages - All Channels"
            show_source = True
        
        if not clean_messages:
            embed = discord.Embed(
                title="✅ No Clean Messages",
                description="No clean messages found.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Sort by timestamp
        clean_messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Pagination
        total_pages = math.ceil(len(clean_messages) / MESSAGES_PER_PAGE)
        page = max(1, min(page, total_pages))
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.green()
        )
        
        start_idx = (page - 1) * MESSAGES_PER_PAGE
        end_idx = start_idx + MESSAGES_PER_PAGE
        page_messages = clean_messages[start_idx:end_idx]
        
        content_lines = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            author_name = msg['author'].display_name
            content = msg['content'] or "*No text content*"
            
            content_lines.append(f"**{i}. {author_name}**")
            content_lines.append(content)
            
            if show_source and 'source_info' in msg:
                content_lines.append(f"📍 {msg['source_info']}")
            
            content_lines.append("")  # Empty line for spacing
        
        embed.description = "\n".join(content_lines)
        embed.set_footer(text=f"Page {page} of {total_pages} | {len(clean_messages)} total messages")
        
        await ctx.send(embed=embed)

    print("Enhanced commands loaded successfully!")
