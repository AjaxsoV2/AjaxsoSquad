from dotenv import load_dotenv
import os

load_dotenv()  # wczytuje zmienne ze standardowego pliku .env

token = os.getenv('DISCORD_TOKEN')

import discord
from discord.ext import commands
import asyncio
import yt_dlp
from yt_dlp.utils import DownloadError

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Funkcja do aktualizacji statusu z ilością osób online (łącznie na wszystkich serwerach)
async def update_presence():
    await bot.wait_until_ready()
    while not bot.is_closed():
        total_online = 0
        for guild in bot.guilds:
            online = sum(m.status != discord.Status.offline and not m.bot for m in guild.members)
            total_online += online
        activity = discord.Game(f"{total_online} osób online")
        await bot.change_presence(activity=activity)
        await asyncio.sleep(60)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')
    bot.loop.create_task(update_presence())

# Komenda pokazująca ilość osób online na serwerze
@bot.command()
async def online(ctx):
    online_count = sum(member.status != discord.Status.offline and not member.bot for member in ctx.guild.members)
    await ctx.send(f"Na serwerze jest obecnie {online_count} osób online.")

# Komenda regulaminu z reakcją i autoryzacją roli
regulamin_message_id = None
regulamin_rola_id = None

@bot.command()
@commands.has_permissions(administrator=True)
async def regulamin(ctx, kanal: discord.TextChannel, rola: discord.Role):
    global regulamin_message_id
    global regulamin_rola_id

    embed = discord.Embed(
        title="📜 Regulamin serwera",
        description=(
            "📢 **Chat.**\n"
            "1. Szanujemy siebie nawzajem.\n"
            "2. Prosi się o nie spamowanie.\n"
            "3. Trzy emotki w jednej wiadomości wystarczą.\n"
            "4. Nie przeklinamy co drugie słowo.\n"
            "5. Zakaz reklamowania się / AUTOMATYCZNY BAN ‼\n"
            "6. Nie wyzywaj.\n"
            "7. Nie spam.\n"
            "8. Pingowanie administracji bez wyraźnego powodu będzie karane BANEM NA 7 DNI.\n\n"
            "🎙 **Kanały głosowe.**\n"
            "1. Nie przeskakujemy z kanału do kanału co chwilę.\n"
            "2. Nie używamy modulatora głosu w dziwne sposoby.\n"
            "3. Uprasza się o nie krzyczenie i robienie przesterów.\n\n"
            "❗ *Nieznajomość regulaminu nie zwalnia z jego przestrzegania.*\n\n"
            "Kliknij ✅ aby zaakceptować regulamin i otrzymać dostęp do serwera."
        ),
        color=discord.Color.blue()
    )

    msg = await kanal.send(embed=embed)
    await msg.add_reaction("✅")

    regulamin_message_id = msg.id
    regulamin_rola_id = rola.id

    await ctx.send(f"✅ Wiadomość regulaminowa wysłana do {kanal.mention}. Reakcja aktywuje rolę: {rola.mention}")

@bot.event
async def on_raw_reaction_add(payload):
    global regulamin_message_id
    global regulamin_rola_id

    if payload.message_id != regulamin_message_id:
        return
    if str(payload.emoji) != "✅":
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    if member is None or member.bot:
        return

    rola = guild.get_role(regulamin_rola_id)
    if rola:
        await member.add_roles(rola)
        print(f"Nadano rolę {rola.name} użytkownikowi {member}")
    else:
        print("❌ Nie znaleziono roli")

# Komenda do puszczania muzyki z YouTube (prosta wersja)
@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ Dołącz najpierw do kanału głosowego!")

    voice_channel = ctx.author.voice.channel

    if not ctx.voice_client:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                if not info['entries']:
                    await ctx.send("❌ Nie znaleziono żadnych wyników.")
                    return
                info = info['entries'][0]
            url = info['url']
    except DownloadError as e:
        await ctx.send(f"❌ Nie mogę odtworzyć tego materiału: {e}")
        return

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    source = discord.FFmpegPCMAudio(url, **ffmpeg_options)

    if vc.is_playing():
        vc.stop()

    vc.play(source)
    await ctx.send(f"🎶 Odtwarzam: **{info.get('title', 'Unknown')}**")

# Komenda zatrzymująca muzykę i rozłączająca bota
@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Bot rozłączył się z kanału głosowego.")
    else:
        await ctx.send("Bot nie jest połączony z żadnym kanałem głosowym.")

bot.run("token")
