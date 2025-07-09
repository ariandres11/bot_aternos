import discord
from discord.ext import commands
from aternosapi import AternosAPI
import secretos

# Configura tus credenciales
headers_cookie = "ATERNOS_SESSION=AuXbFYGj5SmDWJ6L2JdX7dm2wfONUwDC3K6xxoQ3e1KTU4oJQcPdFAsPZ0FM4pV2zZDbJXMchhu548jmIR2O8YP7RWdIdF4Ubxdm; ATERNOS_SEC_xxxxx=yyyyy; ATERNOS_SERVER=84jkIui0VIWl9vQ6"
aternos = AternosAPI(headers_cookie, secretos.TOKEN)


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.command()
async def status(ctx):
    estado = await aternos.GetStatus()
    await ctx.send(f"Estado del servidor: {estado}")

@bot.command()
async def start(ctx):
    resultado = await aternos.StartServer()
    await ctx.send(resultado)

@bot.command()
async def stop(ctx):
    resultado = await aternos.StopServer()
    await ctx.send(resultado)

@bot.command()
async def info(ctx):
    info = await aternos.GetServerInfo()
    await ctx.send(f"Info: {info}")
    
if __name__ == "__main__":
    bot.run(secretos.TOKEN)
