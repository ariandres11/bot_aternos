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

COORDS_FILE = "./coordenadas.json"

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
    if not data:
        embed = discord.Embed(
            title="❌ No hay coordenadas registradas.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🌍 Coordenadas de todos los usuarios",
        color=0x00b894
    )
    for user_id, coords in data.items():
        try:
            member = await ctx.guild.fetch_member(int(user_id))
            username = member.display_name
        except Exception:
            username = f"ID: {user_id}"
        for nombre, info in coords.items():
            emoji = "🌎"
            if "nether" in info["dimension"]:
                emoji = "🔥"
            elif "end" in info["dimension"]:
                emoji = "🟣"
            embed.add_field(
                name=f"{emoji} {nombre} (por {username})",
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

@bot.command(name="help_ari")
async def help_ari(ctx):
    embed = discord.Embed(
        title="📖 Comandos disponibles",
        description="Lista de comandos del bot:",
        color=0x3498db
    )
    embed.add_field(
        name="🟢 $status",
        value="Muestra el estado actual del servidor.",
        inline=False
    )
    embed.add_field(
        name="▶️ $start",
        value="Inicia el servidor.",
        inline=False
    )
    embed.add_field(
        name="⏹️ $stop",
        value="Detiene el servidor.",
        inline=False
    )
    embed.add_field(
        name="ℹ️ $info",
        value="Muestra información del servidor.",
        inline=False
    )
    embed.add_field(
        name="📍 $cargar_coordenadas <nombre> <x> <z> <dimension>",
        value="Guarda una coordenada con nombre, posición y dimensión.",
        inline=False
    )
    embed.add_field(
        name="📒 $coords",
        value="Muestra todas tus coordenadas guardadas.",
        inline=False
    )
    embed.add_field(
        name="🗑️ $borrar_coordenada <nombre>",
        value="Elimina una coordenada guardada por nombre.",
        inline=False
    )
    embed.add_field(
        name="✏️ $editar_coordenada <nombre> <x> <z> <dimension>",
        value="Edita una coordenada existente.",
        inline=False
    )
    embed.add_field(
        name="🔍 $buscar <texto>",
        value="Busca coordenadas por nombre (búsqueda parcial).",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command()
async def buscar(ctx, *, texto: str):
    data = cargar_coordenadas_archivo()
    user_id = str(ctx.author.id)
    user_coords = data.get(user_id, {})
    resultados = []
    texto = texto.lower()
    for nombre, info in user_coords.items():
        if texto in nombre.lower():
            resultados.append((nombre, info))
    if not resultados:
        embed = discord.Embed(
            title="🔍 Sin resultados",
            description=f"No se encontraron coordenadas que contengan: `{texto}`",
            color=0xED4245
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title=f"🔍 Resultados para '{texto}'",
            color=0x5865F2
        )
        for nombre, info in resultados:
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
async def todas_las_coordenadas(ctx):
    data = cargar_coordenadas_archivo()
    if not data:
        embed = discord.Embed(
            title="❌ No hay coordenadas registradas.",
            color=0xED4245
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="🌍 Coordenadas de todos los usuarios",
        color=0x00b894
    )
    for user_id, coords in data.items():
        try:
            member = await ctx.guild.fetch_member(int(user_id))
            username = member.display_name
        except Exception:
            username = f"ID: {user_id}"
        for nombre, info in coords.items():
            emoji = "🌎"
            if "nether" in info["dimension"]:
                emoji = "🔥"
            elif "end" in info["dimension"]:
                emoji = "🟣"
            embed.add_field(
                name=f"{emoji} {nombre} (por {username})",
                value=f"📍 `{info['coordenadas']}`\n🌐 `{info['dimension']}`",
                inline=False
            )
    await ctx.send(embed=embed)

bot.remove_command('help')

if __name__ == "__main__":
    bot.run(secretos.TOKEN)
