import discord
from discord.ext import commands
from api import AternosAPI
import secretos
import json
import os

# Configura tus credenciales
headers_cookie = "ATERNOS_SESSION=AuXbFYGj5SmDWJ6L2JdX7dm2wfONUwDC3K6xxoQ3e1KTU4oJQcPdFAsPZ0FM4pV2zZDbJXMchhu548jmIR2O8YP7RWdIdF4Ubxdm; ATERNOS_SEC_xxxxx=yyyyy; ATERNOS_SERVER=84jkIui0VIWl9vQ6"
aternos = AternosAPI(headers_cookie, secretos.TOKEN)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

COORDS_FILE = "coordenadas.json"

def cargar_coordenadas_archivo():
    if not os.path.exists(COORDS_FILE):
        with open(COORDS_FILE, "w") as f:
            json.dump({}, f)
    with open(COORDS_FILE, "r") as f:
        return json.load(f)

def guardar_coordenadas_archivo(data):
    with open(COORDS_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

@bot.command()
async def cargar_coordenadas(ctx, nombre: str, x: int, z: int, dimension: str):
    data = cargar_coordenadas_archivo()
    user_id = str(ctx.author.id)
    user_coords = data.setdefault(user_id, {})
    user_coords[nombre] = {
        "coordenadas": f"{x} {z}",
        "dimension": dimension.lower()
    }
    guardar_coordenadas_archivo(data)
    embed = discord.Embed(
        title="✅ Coordenada guardada",
        description=f"**{nombre}**\n📍 Coordenadas: `{x} {z}`\n🌎 Dimensión: `{dimension.lower()}`",
        color=0x57F287
    )
    await ctx.send(embed=embed)

@bot.command()
async def coords(ctx):
    data = cargar_coordenadas_archivo()
    user_id = str(ctx.author.id)
    user_coords = data.get(user_id, {})
    if not user_coords:
        embed = discord.Embed(
            title="❌ No tienes coordenadas guardadas.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="📒 Tus coordenadas",
            color=0x5865F2
        )
        for nombre, info in user_coords.items():
            emoji = "🌎"
            if "nether" in info["dimension"]:
                emoji = "🔥"
            elif "end" in info["dimension"]:
                emoji = "🟣"
            embed.add_field(
                name=f"{emoji} {nombre}",
                value=f"📍 `{info['coordenadas']}`\n🌐 `{info['dimension']}`",
                inline=False
            )
        await ctx.send(embed=embed)

@bot.command()
async def borrar_coordenada(ctx, nombre: str):
    data = cargar_coordenadas_archivo()
    user_id = str(ctx.author.id)
    user_coords = data.get(user_id, {})
    if nombre in user_coords:
        del user_coords[nombre]
        data[user_id] = user_coords
        guardar_coordenadas_archivo(data)
        embed = discord.Embed(
            title="🗑️ Coordenada eliminada",
            description=f"Se eliminó **{nombre}**.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ No existe esa coordenada.",
            color=0xED4245
        )
        await ctx.send(embed=embed)

@bot.command()
async def editar_coordenada(ctx, nombre: str, x: int, z: int, dimension: str):
    data = cargar_coordenadas_archivo()
    user_id = str(ctx.author.id)
    user_coords = data.get(user_id, {})
    if nombre in user_coords:
        user_coords[nombre] = {
            "coordenadas": f"{x} {z}",
            "dimension": dimension.lower()
        }
        data[user_id] = user_coords
        guardar_coordenadas_archivo(data)
        embed = discord.Embed(
            title="✏️ Coordenada actualizada",
            description=f"**{nombre}** ahora es `{x} {z}` en `{dimension.lower()}`",
            color=0xFEE75C
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ No existe esa coordenada.",
            color=0xED4245
        )
        await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(secretos.TOKEN)
