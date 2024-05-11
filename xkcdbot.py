import discord,os,requests,io,random,subprocess
from discord.ext import commands
from dotenv import load_dotenv

# to make bot https://discord.com/developers/applications/
# add DISCORD_TOKEN=(discordtoken) to .env file in same directory
# set your prefix aswell in .env as PREFIX=! or whatever you want instead of !

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = os.getenv('PREFIX')
service_name = 'neonxkcdbot'
script_path = os.path.abspath(__file__)
response = None
intents = discord.Intents.default()
intents.message_content = True
intents.guild_messages = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

async def responding(ctx, comic_id):
    if comic_id == "":
        response = requests.get('https://xkcd.com/info.0.json')
    else:
        response = requests.get(f'https://xkcd.com/{comic_id}/info.0.json')
    if response.status_code == 200:
        data = response.json()
        comic_url = data['img']
        alt_text = data['alt']
        explain_url = f'https://www.explainxkcd.com/wiki/index.php/{data["num"]}'
        image_response = requests.get(comic_url)
        if image_response.status_code == 200:
            image_data = image_response.content
            file = discord.File(io.BytesIO(image_data), filename='comic.png')
            message = f'.\n**Alt Text:** {alt_text}\n[Explain XKCD {comic_id} ]({explain_url})'
            await ctx.send(file=file, content=message)
        else:
            await ctx.send('Failed to fetch XKCD comic image')
    else:
        await ctx.send('Failed to fetch XKCD comic')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    app_info = await bot.application_info()
    bot.owner_id = app_info.owner.id
    print(f'Owner ID: {bot.owner_id}')

@bot.command(name='xkcd')
async def xkcd_command(ctx, comic_id: str = 'latest'):
    if comic_id == 'latest' or not comic_id:
        latest_response = requests.get('https://xkcd.com/info.0.json')
        if latest_response.status_code == 200:
            latest_data = latest_response.json()
            latest_comic_num = latest_data['num']
        await responding(ctx, latest_comic_num)
    elif comic_id == 'random':
        latest_response = requests.get('https://xkcd.com/info.0.json')
        if latest_response.status_code == 200:
            latest_data = latest_response.json()
            latest_comic_num = latest_data['num']
            random_comic_num = random.randint(1, latest_comic_num)
            await responding(ctx, random_comic_num)
        else:
            await ctx.send('Failed to fetch latest XKCD comic')
            return
    elif comic_id.isdigit():
        comic_num = int(comic_id)
        latest_response = requests.get('https://xkcd.com/info.0.json')
        if latest_response.status_code == 200:
            latest_data = latest_response.json()
            latest_comic_num = latest_data['num']
            if comic_num > 0 and comic_num <= latest_comic_num:
                await responding(ctx, comic_num)
            else:
                await ctx.send('Comic number is out of range')
                return
        else:
            await ctx.send('Failed to fetch latest XKCD comic')
            return
    elif comic_id == 'killbot':
        if ctx.message.author.id == bot.owner_id:
            await ctx.send('Shutting down...')
            await bot.close()
            os._exit(0)
        else:
            await ctx.send('You are not the owner of this bot.')
    elif comic_id == 'serviceadd':
            if ctx.message.author.id == bot.owner_id:
                service_file = f'/etc/systemd/system/{service_name}.service'
                if os.path.exists(service_file):
                    await ctx.send(f'Service file already exists for {service_name}.')
                else:
                    service_content = f'''
        [Unit]
        Description=Neon XKCD Bot
        After=network.target

        [Service]
        ExecStart=python3 {script_path}
        WorkingDirectory={os.path.dirname(script_path)}
        Restart=always

        [Install]
        WantedBy=multi-user.target
        '''
                    with subprocess.Popen(['sudo', 'tee', service_file], stdin=subprocess.PIPE) as proc:
                        proc.stdin.write(service_content.encode())
                        proc.stdin.close()
                        proc.wait()
                        subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
                        await ctx.send(f'Service file created for {service_name}.')
            else:
                await ctx.send('You are not the owner of this bot.')
    elif comic_id == 'serviceremove':
        if ctx.message.author.id == bot.owner_id:
            service_file = f'/etc/systemd/system/{service_name}.service'
            if os.path.exists(service_file):
                subprocess.run(['sudo', 'rm', service_file])
                subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
                await ctx.send(f'Service file deleted for {service_name}.')
            else:
                await ctx.send(f'Service file does not exist for {service_name}.')
        else:
            await ctx.send('You are not the owner of this bot.')            
    else:
        help_message = (
            ".\nHelp message\n\n"
            f"To get the latest XKCD comic, use `{PREFIX}xkcd`\n"
            f"To get a random XKCD comic, use `{PREFIX}xkcd random`\n"
            f"To get a specific XKCD comic, use `{PREFIX}xkcd <comic_id>`\n"
            f"To see this message again, use `{PREFIX}xkcd help`\n"
        )
        if ctx.message.author.id == bot.owner_id:
            help_message += f"\nIf you are the bot owner, you can start or stop the service using `{PREFIX}xkcd serviceadd` or `{PREFIX}xkcd serviceremove`"
        await ctx.send(help_message)
        return

bot.run(TOKEN)
