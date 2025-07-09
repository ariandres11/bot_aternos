import discord
from discord.ext import commands
import requests
import secretos
import json
import asyncio
import re

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix = '$', intents=intents)

class AternosAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Referer': 'https://aternos.org/',
            'X-Requested-With': 'XMLHttpRequest'
        })
        self.logged_in = False
        self.servers = []
        self.current_server = None

    # Se loguea con mi token de sesión
        
    async def login_with_session(self, session_token):
        """Login usando token de sesión"""
        try:
            # Configurar cookie de sesión
            self.session.cookies.set('ATERNOS_SESSION', session_token, domain='aternos.org')
            
            # Verificar si la sesión es válida
            response = self.session.get('https://aternos.org/servers/')
            
            if response.status_code == 200 and ('servers' in response.text or 'panel' in response.text):
                self.logged_in = True
                print("✅ Login exitoso con token de sesión")
                await self.get_servers()
                return True
            else:
                print("❌ Token de sesión inválido o expirado")
                print(f"Status code: {response.status_code}")
                
        except Exception as e:
            print(f"Error en login con sesión: {e}")
        
        return False
    
    # Ve la página de servidores en busca de servidores
    async def get_servers(self):
        """Obtener lista de servidores parseando HTML"""
        if not self.logged_in:
            return []
        
        try:
            response = self.session.get('https://aternos.org/servers/')
            print(f"Getting servers - Status: {response.status_code}")
            
            if response.status_code == 200:
                html_content = response.text
                self.servers = self.parse_servers_from_html(html_content)
                print(f"✅ Servidores parseados del HTML: {len(self.servers)}")
                
                # Limpiar duplicados manteniendo el primero de cada ID
                unique_servers = {}
                for server in self.servers:
                    server_id = server.get('id')
                    if server_id not in unique_servers:
                        unique_servers[server_id] = server
                
                self.servers = list(unique_servers.values())
                print(f"✅ Servidores únicos: {len(self.servers)}")
                
                for i, server in enumerate(self.servers):
                    print(f"Servidor {i+1}: {server}")
                
                return self.servers
                        
        except Exception as e:
            print(f"Error obteniendo servidores: {e}")
        
        return []
    
    def parse_servers_from_html(self, html_content):
        """Parsear servidores del HTML de Aternos con mejor detección"""
        servers = []
        
        try:
            # Buscar el patrón más confiable primero
            pattern = r'data-id="([^"]+)"[^>]*>.*?<.*?class="[^"]*name[^"]*"[^>]*>([^<]+)<'
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            
            if matches:
                print(f"Encontrado patrón confiable - {len(matches)} matches")
                for server_id, name in matches:
                    clean_name = re.sub(r'<[^>]*>', '', name).strip()
                    servers.append({
                        'id': server_id,
                        'name': clean_name,
                        'displayname': clean_name,
                        'software': 'Minecraft',
                        'status': 'unknown'
                    })
                    print(f"Servidor agregado: ID={server_id}, Name={clean_name}")
                    
        except Exception as e:
            print(f"Error parseando HTML: {e}")
        
        return servers
    

    # Info de servidor específico hardcoded
    # TODO: No hardcodear, entrar a uno definido por argumentos
    async def select_server(self, server_identifier):
        """Seleccionar un servidor específico por nombre o ID"""
        if not self.logged_in:
            return False, "No conectado a Aternos"
        
        target_server = None
        
        # Buscar el servidor por ID específicamente
        if server_identifier == "LabForkRecargado" or server_identifier == "84jkIui0VIWl9vQ6":
            for server in self.servers:
                if server.get('id') == '84jkIui0VIWl9vQ6':
                    target_server = server
                    print(f"✅ Encontrado servidor por ID: {target_server}")
                    break
        
        if not target_server:
            for server in self.servers:
                if (server.get('name', '').lower() == server_identifier.lower() or 
                    server.get('displayname', '').lower() == server_identifier.lower() or 
                    server.get('id') == server_identifier):
                    target_server = server
                    break
        
        if not target_server:
            available_servers = [f"{s.get('name', 'Sin nombre')} (ID: {s.get('id', 'N/A')})" for s in self.servers]
            return False, f"Servidor '{server_identifier}' no encontrado. Disponibles: {', '.join(available_servers)}"
        
        try:
            server_id = target_server['id']
            server_url = f'https://aternos.org/server/{server_id}'
            
            response = self.session.get(server_url)
            
            if response.status_code == 200:
                self.current_server = target_server
                print(f"✅ Accedido al servidor: {target_server['name']} ({server_id})")
                return True, f"Conectado al servidor {target_server['name']} (ID: {server_id})"
            else:
                return False, f"Error accediendo al servidor (Status: {response.status_code})"
                
        except Exception as e:
            return False, f"Error: {e}"
    
    async def get_server_status_detailed(self):
        """Obtener estado detallado del servidor accediendo a su página"""
        if not self.current_server:
            return None, "No hay servidor seleccionado"
        
        try:
            server_id = self.current_server['id']
            server_url = f'https://aternos.org/server/{server_id}'
            
            # Acceder a la página del servidor
            response = self.session.get(server_url)
            print(f"Accediendo a página del servidor: {response.status_code}")
            
            if response.status_code == 200:
                html = response.text
                
                # Buscar indicadores de estado en el HTML
                status_info = {
                    'page_loaded': True,
                    'has_start_button': 'start' in html.lower() and 'button' in html.lower(),
                    'has_stop_button': 'stop' in html.lower() and 'button' in html.lower(),
                    'has_console': 'console' in html.lower(),
                    'server_online': False,
                    'server_offline': True,
                    'server_starting': False,
                    'raw_indicators': []
                }
                
                # Buscar patrones específicos de estado
                online_patterns = [
                    r'status.*?online',
                    r'server.*?running',
                    r'players.*?online',
                    r'stop.*?server'
                ]
                
                offline_patterns = [
                    r'status.*?offline',
                    r'server.*?stopped',
                    r'start.*?server',
                    r'server.*?not.*?running'
                ]
                
                starting_patterns = [
                    r'server.*?starting',
                    r'status.*?starting',
                    r'preparing.*?server'
                ]
                
                for pattern in online_patterns:
                    if re.search(pattern, html, re.IGNORECASE):
                        status_info['server_online'] = True
                        status_info['server_offline'] = False
                        status_info['raw_indicators'].append(f"Online: {pattern}")
                
                for pattern in starting_patterns:
                    if re.search(pattern, html, re.IGNORECASE):
                        status_info['server_starting'] = True
                        status_info['server_offline'] = False
                        status_info['raw_indicators'].append(f"Starting: {pattern}")
                
                # Buscar elementos de la interfaz
                if 'start server' in html.lower():
                    status_info['can_start'] = True
                    status_info['server_offline'] = True
                if 'stop server' in html.lower():
                    status_info['can_stop'] = True
                    status_info['server_online'] = True
                    status_info['server_offline'] = False
                
                return status_info, "Estado parseado desde página del servidor"
            else:
                return None, f"Error accediendo a página del servidor: {response.status_code}"
                
        except Exception as e:
            return None, f"Error: {e}"
    
    async def get_console_log(self):
        """Obtener los últimos mensajes de la consola del servidor"""
        if not self.current_server:
            return None, "No hay servidor seleccionado"
        
        try:
            server_id = self.current_server['id']
            
            # Primero ir a la página de consola del servidor
            console_page_url = f'https://aternos.org/server/{server_id}/console'
            console_response = self.session.get(console_page_url)
            
            print(f"Accediendo a consola: {console_response.status_code}")
            
            if console_response.status_code == 200:
                # Buscar token CSRF en la página de consola
                csrf_token = None
                csrf_match = re.search(r'_token["\']?\s*[:=]\s*["\']([^"\']+)["\']', console_response.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    print(f"Token CSRF encontrado para consola: {csrf_token}")
                
                # Probar diferentes endpoints para obtener log de consola
                log_endpoints = [
                    {
                        'url': f'https://aternos.org/panel/ajax/console/log.php',
                        'params': {'id': server_id},
                        'headers': {'X-Requested-With': 'XMLHttpRequest'}
                    },
                    {
                        'url': f'https://aternos.org/server/{server_id}/console/log',
                        'params': {'_token': csrf_token} if csrf_token else {},
                        'headers': {'X-Requested-With': 'XMLHttpRequest'}
                    }
                ]
                
                for i, endpoint in enumerate(log_endpoints, 1):
                    print(f"Probando endpoint de log {i}: {endpoint['url']}")
                    
                    response = self.session.get(
                        endpoint['url'], 
                        params=endpoint['params'],
                        headers=endpoint['headers']
                    )
                    
                    print(f"Log response {i}: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            # Intentar parsear como JSON
                            result = response.json()
                            if 'log' in result or 'console' in result or 'messages' in result:
                                return result, "Log JSON obtenido"
                        except json.JSONDecodeError:
                            # Si no es JSON, analizar el HTML
                            html_content = response.text
                            if 'console' in html_content.lower() or 'log' in html_content.lower():
                                return {
                                    'html_log': html_content[:1000],
                                    'content_type': 'general_html'
                                }, f"HTML con contenido de log"
                
                return {
                    'page_content': console_response.text[:1000],
                    'note': 'Página de consola accesible pero sin datos específicos'
                }, "Página de consola obtenida"
            
            return None, "No se pudo obtener el log de la consola"
            
        except Exception as e:
            return None, f"Error: {e}"
    
    async def get_player_info_read_only(self, player_name):
        """Obtener información de jugador usando comandos de solo lectura"""
        if not self.current_server:
            return None, "No hay servidor seleccionado"
        
        try:
            server_id = self.current_server['id']
            
            # Intentar obtener información desde la página del servidor
            # Nota: Esta información será limitada ya que no enviamos comandos
            player_info = {
                'player_name': player_name,
                'server_access': True,
                'note': 'Información limitada - modo solo lectura'
            }
            
            # Acceder a la página del servidor para obtener información general
            server_response = self.session.get(f'https://aternos.org/server/{server_id}')
            
            if server_response.status_code == 200:
                html = server_response.text.lower()
                
                # Buscar indicadores de jugadores online
                if 'players' in html and 'online' in html:
                    player_info['server_has_players'] = True
                else:
                    player_info['server_has_players'] = False
                
                # Buscar información del mundo
                if 'overworld' in html:
                    player_info['world_overworld'] = True
                if 'nether' in html:
                    player_info['world_nether'] = True
                if 'end' in html:
                    player_info['world_end'] = True
            
            return player_info, "Información básica obtenida (modo solo lectura)"
            
        except Exception as e:
            return None, f"Error: {e}"
    
    async def send_console_command(self, command):
        """Enviar comando a la consola del servidor y obtener respuesta"""
        if not self.current_server:
            return False, "No hay servidor seleccionado"
        
        try:
            server_id = self.current_server['id']
            
            # Acceder a la página de consola primero
            console_url = f'https://aternos.org/server/{server_id}/console'
            console_response = self.session.get(console_url)
            
            if console_response.status_code != 200:
                return False, f"Error accediendo a consola: {console_response.status_code}"
            
            # Buscar token CSRF
            csrf_token = None
            csrf_patterns = [
                r'_token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'csrf[_-]?token["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'token["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in csrf_patterns:
                csrf_match = re.search(pattern, console_response.text, re.IGNORECASE)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
                    break
            
            # Preparar datos para enviar comando
            command_data = {
                'command': command.lstrip('/'),
                '_token': csrf_token
            }
            
            # Headers para la petición
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': console_url
            }
            
            # Intentar diferentes endpoints para enviar comandos
            command_endpoints = [
                f'https://aternos.org/server/{server_id}/console/command',
                f'https://aternos.org/panel/ajax/console/command.php',
                f'https://aternos.org/server/{server_id}/command'
            ]
            
            for endpoint in command_endpoints:
                response = self.session.post(
                    endpoint,
                    data=command_data,
                    headers=headers
                )
                
                print(f"Comando enviado a {endpoint}: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        return True, f"Comando enviado exitosamente: {result}"
                    except json.JSONDecodeError:
                        if 'success' in response.text.lower() or 'ok' in response.text.lower():
                            return True, "Comando enviado (respuesta HTML)"
                        else:
                            return False, f"Respuesta inesperada: {response.text[:200]}"
            
            return False, "No se pudo enviar el comando a ningún endpoint"
            
        except Exception as e:
            return False, f"Error enviando comando: {e}"
    
    async def send_command_with_response_capture(self, command, timeout=10):
        """Enviar comando y capturar la respuesta real esperando en el log"""
        if not self.current_server:
            return False, "No hay servidor seleccionado", None

        try:
            server_id = self.current_server['id']

            # 1. Obtener timestamp actual o últimas líneas del log
            log_before = await self.get_console_log_simple()
            lines_before = self.extract_log_lines(log_before)

            print(f"Líneas antes del comando: {len(lines_before)}")

            # 2. Enviar el comando
            success, send_response = await self.send_console_command(command)

            if not success:
                return False, send_response, None

            print(f"Comando enviado: {command}")

            # 3. Esperar y polling del log hasta encontrar respuesta
            for attempt in range(timeout):
                await asyncio.sleep(1)  # Esperar 1 segundo entre intentos

                log_after = await self.get_console_log_simple()
                lines_after = self.extract_log_lines(log_after)

                # Buscar nuevas líneas
                new_lines = []
                for line in lines_after:
                    if line not in lines_before:
                        new_lines.append(line)

                # Imprimir todas las líneas nuevas detectadas
                if new_lines:
                    print(f"Intento {attempt + 1}: {len(new_lines)} líneas nuevas:")
                    for idx, l in enumerate(new_lines, 1):
                        print(f"  [{idx}] {l}")
                else:
                    print(f"Intento {attempt + 1}: 0 líneas nuevas, ninguna es respuesta del comando")

                # Buscar respuesta específica del comando
                for line in new_lines:
                    if self.is_command_response(line, command):
                        print(f"Respuesta encontrada: {line}")
                        return True, "Respuesta capturada", line

            return True, f"Comando enviado pero respuesta no encontrada en {timeout} segundos", None

        except Exception as e:
            print(f"Error: {e}")
            return False, f"Error: {e}", None
    
    async def get_console_log_simple(self):
        """Obtener log de consola de forma más directa"""
        if not self.current_server:
            return None
        
        try:
            server_id = self.current_server['id']
            
            # Probar endpoints de log
            endpoints = [
                f'https://aternos.org/panel/ajax/console/log.php?id={server_id}',
                f'https://aternos.org/server/{server_id}/console/log',
                f'https://aternos.org/ajax/console/log?server={server_id}'
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(
                        endpoint,
                        headers={'X-Requested-With': 'XMLHttpRequest'},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        # Intentar JSON primero
                        try:
                            json_data = response.json()
                            return json_data
                        except:
                            # Si no es JSON, procesar como texto
                            text = response.text
                            if len(text) > 10:  # Verificar que tiene contenido
                                return {'text': text}
                except:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error obteniendo log simple: {e}")
            return None
    
    def extract_log_lines(self, log_data):
        """Extraer líneas individuales del log"""
        if not log_data:
            return []
        
        try:
            # Si es JSON con campo log
            if isinstance(log_data, dict):
                if 'log' in log_data:
                    text = str(log_data['log'])
                elif 'console' in log_data:
                    text = str(log_data['console'])
                elif 'messages' in log_data:
                    text = str(log_data['messages'])
                elif 'text' in log_data:
                    text = log_data['text']
                else:
                    text = str(log_data)
            else:
                text = str(log_data)
            
            # Dividir en líneas y limpiar
            lines = []
            for line in text.split('\n'):
                clean_line = line.strip()
                if clean_line and len(clean_line) > 5:  # Filtrar líneas muy cortas
                    lines.append(clean_line)
            
            return lines[-50:]  # Solo las últimas 50 líneas para eficiencia
            
        except Exception as e:
            print(f"Error extrayendo líneas: {e}")
            return []
    
    def is_command_response(self, line, command):
        """Verificar si una línea es la respuesta del comando enviado"""
        try:
            line_lower = line.lower()
            
            # Patrones para respuestas de comandos /data get
            if 'data get' in command.lower():
                # Buscar patrón típico: "PlayerName has the following entity data:"
                if 'has the following entity data' in line_lower:
                    return True
                # O directamente datos en formato JSON-like
                if '{' in line and '}' in line:
                    return True
            
            # Patrones para otros comandos
            if 'say' in command.lower():
                if '[server]' in line_lower or 'server' in line_lower:
                    return True
            
            if 'gamerule' in command.lower():
                if 'gamerule' in line_lower and ('set to' in line_lower or 'is now' in line_lower):
                    return True
            
            # Buscar el nombre del jugador del comando en la respuesta
            command_parts = command.split()
            for part in command_parts:
                if len(part) > 3 and part in line:  # Buscar partes significativas del comando
                    # Si contiene números o datos, probablemente es respuesta
                    if any(char.isdigit() for char in line):
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error verificando respuesta: {e}")
            return False

    async def get_player_info_with_real_capture(self, player_name):
        """Obtener información real capturando respuestas del log"""
        if not self.current_server:
            return None, "No hay servidor seleccionado"

        # Verificar si la captura real es posible
        log_test = await self.get_console_log_simple()
        if not log_test or (isinstance(log_test, dict) and not any(k in log_test for k in ['log', 'console', 'messages', 'text'])):
            return None, "⚠️ No es posible capturar respuestas reales del log en este servidor. Aternos no expone el log por HTTP."

        info_results = {}
        
        # Comandos para información básica
        commands_to_execute = {
            'health': f'data get entity {player_name} Health',
            'position': f'data get entity {player_name} Pos',
            'xp_level': f'data get entity {player_name} XpLevel',
            'dimension': f'data get entity {player_name} Dimension',
            'gamemode': f'data get entity {player_name} playerGameType'
        }
        
        for info_name, command in commands_to_execute.items():
            print(f"Ejecutando comando para {info_name}: {command}")
            
            success, response, real_data = await self.send_command_with_response_capture(command, timeout=8)
            
            info_results[info_name] = {
                'success': success,
                'response': response,
                'real_data': real_data,
                'command': command
            }
            
            print(f"Resultado {info_name}: success={success}, real_data={real_data}")
            
            # Pausa entre comandos
            await asyncio.sleep(2)
        
        return info_results, "Comandos ejecutados con captura de respuesta"

    async def get_player_stats_with_real_numbers(self, player_name):
        """Obtener estadísticas reales del jugador con números específicos"""
        if not self.current_server:
            return None, "No hay servidor seleccionado"
        
        stats_results = {}
        
        # Comandos específicos para estadísticas con números
        stats_commands = {
            'vida': f'data get entity {player_name} Health',
            'nivel_xp': f'data get entity {player_name} XpLevel',
            'posicion': f'data get entity {player_name} Pos',
            'dimension': f'data get entity {player_name} Dimension',
            'bloques_destruidos': f'data get entity {player_name} Stats.minecraft:mined',
            'muertes': f'data get entity {player_name} Stats.minecraft:deaths',
            'tiempo_jugado': f'data get entity {player_name} Stats.minecraft:play_one_minute',
            'distancia_caminada': f'data get entity {player_name} Stats.minecraft:walk_one_cm',
            'items_crafteados': f'data get entity {player_name} Stats.minecraft:craft_item',
            'mobs_matados': f'data get entity {player_name} Stats.minecraft:kill_entity'
        }
        
        print(f"🔍 Obteniendo estadísticas de {player_name}...")
        
        for stat_name, command in stats_commands.items():
            print(f"📤 Ejecutando: {command}")
            
            try:
                success, response, real_data = await self.send_command_with_response_capture(command, timeout=10)
                
                stats_results[stat_name] = {
                    'success': success,
                    'response': response,
                    'real_data': real_data,
                    'command': command
                }
                
                print(f"✅ {stat_name}: {'Capturado' if real_data else 'Sin captura'}")
                
                # Pausa más larga entre comandos de estadísticas
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error en {stat_name}: {e}")
                stats_results[stat_name] = {
                    'success': False,
                    'response': f"Error: {e}",
                    'real_data': None,
                    'command': command
                }
        
        return stats_results, "Estadísticas ejecutadas con captura de respuesta"

    async def get_live_console_data(self):
        """Obtener datos de consola en tiempo real (método simplificado)"""
        if not self.current_server:
            return None
        
        try:
            server_id = self.current_server['id']
            
            # Probar múltiples endpoints para obtener datos de consola
            endpoints_to_try = [
                {
                    'url': f'https://aternos.org/panel/ajax/console/log.php?id={server_id}',
                    'method': 'ajax_log'
                },
                {
                    'url': f'https://aternos.org/server/{server_id}/console',
                    'method': 'page_scraping'
                }
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    if endpoint['method'] == 'ajax_log':
                        response = self.session.get(
                            endpoint['url'],
                            headers={'X-Requested-With': 'XMLHttpRequest'},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            try:
                                json_data = response.json()
                                if json_data:
                                    return {
                                        'method': 'ajax_log',
                                        'content': json_data,
                                        'raw': response.text
                                    }
                            except:
                                text_content = response.text
                                if len(text_content) > 10:
                                    return {
                                        'method': 'ajax_log_text',
                                        'content': text_content,
                                        'raw': text_content
                                    }
                    
                    elif endpoint['method'] == 'page_scraping':
                        response = self.session.get(endpoint['url'])
                        
                        if response.status_code == 200:
                            html = response.text
                            
                            # Buscar contenido de consola en el HTML
                            console_patterns = [
                                r'<div[^>]*class="[^"]*console[^"]*"[^>]*>(.*?)</div>',
                                r'<pre[^>]*class="[^"]*log[^"]*"[^>]*>(.*?)</pre>',
                                r'"console":\s*"([^"]*)"',
                                r'"log":\s*"([^"]*)"'
                            ]
                            
                            for pattern in console_patterns:
                                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                                if matches:
                                    console_content = matches[0]
                                    # Limpiar HTML
                                    clean_content = re.sub(r'<[^>]*>', '', console_content)
                                    clean_content = clean_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                                    
                                    if len(clean_content) > 20:
                                        return {
                                            'method': 'page_scraping',
                                            'content': clean_content,
                                            'raw': console_content
                                        }
                
                except Exception as e:
                    print(f"Error en endpoint {endpoint['method']}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error en get_live_console_data: {e}")
            return None

    def extract_lines_from_console(self, console_data):
        """Extraer líneas de texto del contenido de consola"""
        if not console_data:
            return []
        
        try:
            content = console_data.get('content', '')
            
            if isinstance(content, dict):
                # Si es JSON, buscar campos de log
                text = ''
                for key in ['log', 'console', 'messages', 'output', 'data']:
                    if key in content:
                        text = str(content[key])
                        break
                if not text:
                    text = str(content)
            else:
                text = str(content)
            
            # Dividir en líneas y limpiar
            lines = []
            for line in text.split('\n'):
                clean_line = line.strip()
                if clean_line and len(clean_line) > 10:  # Filtrar líneas muy cortas
                    # Remover timestamps y formateo extra
                    clean_line = re.sub(r'^\[[\d\:\-\s]+\]\s*', '', clean_line)
                    clean_line = re.sub(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s*', '', clean_line)
                    if clean_line:
                        lines.append(clean_line)
            
            # Retornar solo las últimas 20 líneas para eficiencia
            return lines[-20:] if lines else []
            
        except Exception as e:
            print(f"Error extrayendo líneas: {e}")
            return []

    def is_command_response_improved(self, line, command):
        """Detectar si una línea es respuesta del comando con mejor precisión"""
        try:
            line_lower = line.lower()
            command_lower = command.lower()
            
            # Para comandos /data get entity
            if 'data get entity' in command_lower:
                # Extraer nombre del jugador del comando
                command_parts = command.split()
                if len(command_parts) >= 4:
                    player_name = command_parts[3]
                    
                    # Buscar respuesta específica con el nombre del jugador
                    if player_name.lower() in line_lower:
                        # Patrones específicos de respuesta
                        response_patterns = [
                            'has the following entity data',
                            'entity data',
                            'no entity was found',
                            'not found',
                            'does not exist'
                        ]
                        
                        for pattern in response_patterns:
                            if pattern in line_lower:
                                return True
                        
                        # También buscar datos numéricos
                        if any(char.isdigit() for char in line):
                            return True
            
            # Para otros comandos
            if 'say' in command_lower and '[server]' in line_lower:
                return True
            
            if 'gamerule' in command_lower and 'gamerule' in line_lower:
                return True
            
            return False
            
        except Exception as e:
            print(f"Error verificando respuesta: {e}")
            return False

    async def send_command_and_capture_response_debug(self, command, wait_time=5):
        """Enviar comando y capturar respuesta con debug detallado"""
        if not self.current_server:
            return False, "No hay servidor seleccionado", None
        
        print(f"\n{'='*50}")
        print(f"🚀 INICIANDO DEBUG PARA COMANDO: {command}")
        print(f"{'='*50}")
        
        try:
            # 1. Capturar estado inicial de la consola
            print("📡 PASO 1: Capturando estado inicial de consola...")
            initial_console = await self.get_live_console_data()
            initial_lines = self.extract_lines_from_console(initial_console)
            
            print(f"🔍 Líneas iniciales encontradas: {len(initial_lines)}")
            if initial_lines:
                print("📝 Últimas 3 líneas iniciales:")
                for i, line in enumerate(initial_lines[-3:], 1):
                    print(f"  {i}. {line}")
            
            # 2. Enviar el comando
            print(f"\n📤 PASO 2: Enviando comando: {command}")
            success, send_response = await self.send_console_command(command)
            
            if not success:
                print(f"❌ Error enviando comando: {send_response}")
                return False, send_response, None
            
            print(f"✅ Comando enviado exitosamente. Respuesta: {send_response}")
            
            # 3. Monitorear cambios en tiempo real
            print(f"\n⏳ PASO 3: Monitoreando respuesta por {wait_time} segundos...")
            
            for attempt in range(wait_time):
                print(f"\n--- Intento {attempt + 1}/{wait_time} ---")
                await asyncio.sleep(1)
                
                current_console = await self.get_live_console_data()
                current_lines = self.extract_lines_from_console(current_console)
                
                print(f"📊 Total de líneas actuales: {len(current_lines)}")
                
                # Buscar nuevas líneas
                new_lines = []
                for line in current_lines:
                    if line not in initial_lines and line not in new_lines:
                        new_lines.append(line)
                
                print(f"🆕 Nuevas líneas encontradas: {len(new_lines)}")
                
                if new_lines:
                    print("📝 NUEVAS LÍNEAS DETECTADAS:")
                    for i, line in enumerate(new_lines, 1):
                        print(f"  {i}. {line}")
                        
                        # Verificar si es respuesta del comando
                        if self.is_command_response_improved(line, command):
                            print(f"🎯 ¡RESPUESTA DEL COMANDO ENCONTRADA!: {line}")
                            return True, "Respuesta capturada exitosamente", line
                else:
                    print("   (No hay nuevas líneas)")
                
                # Mostrar también las últimas líneas para contexto
                if current_lines:
                    print("📄 Últimas 2 líneas de la consola:")
                    for i, line in enumerate(current_lines[-2:], 1):
                        print(f"  {i}. {line}")
            
            print(f"\n⚠️ RESULTADO: Comando enviado pero respuesta específica no encontrada en {wait_time} segundos")
            print("💡 Posibles razones:")
            print("   - El jugador no está conectado")
            print("   - El comando no es válido")
            print("   - El sistema de captura necesita ajustes")
            
            return True, f"Comando enviado pero respuesta específica no encontrada en {wait_time} segundos", None
            
        except Exception as e:
            print(f"❌ ERROR EN DEBUG: {e}")
            return False, f"Error: {e}", None

# Instancia global de la API
aternos = AternosAPI()

@bot.event
async def on_ready():
    print(f"Estamos in! {bot.user}")
    
    session_token = "kuOEttlHbDya6t4HaykjLLPf6GFkUEEKjcHvSw50Woluq370yAvptgTE2pHCdNN4rfZcJyq6CcMhNyHPPiTN2JGjQAxnbFEdkBZq"
    
    print("Intentando conectar a Aternos con token de sesión...")
    success = await aternos.login_with_session(session_token)
    if success:
        print(f"✅ Conectado a Aternos! Servidores encontrados: {len(aternos.servers)}")
        
        # Intentar seleccionar automáticamente por ID
        success, message = await aternos.select_server("84jkIui0VIWl9vQ6")
        if success:
            print(f"✅ {message}")
        else:
            print(f"⚠️ {message}")
    else:
        print("❌ Error conectando a Aternos")

@bot.command()
async def labfork(ctx):
    """Acceso rápido al servidor LabForkRecargado por ID"""
    if not aternos.logged_in:
        await ctx.send("❌ No conectado a Aternos")
        return
    
    success, message = await aternos.select_server("84jkIui0VIWl9vQ6")
    
    embed = discord.Embed(
        title="🔬 LabForkRecargado",
        description=message,
        color=0x00ff00 if success else 0xff0000
    )
    
    if success:
        embed.add_field(name="ID", value="84jkIui0VIWl9vQ6", inline=True)
        embed.add_field(name="Nombre", value=aternos.current_server['name'], inline=True)
        embed.add_field(name="Comandos Disponibles", value="`$status` - Ver estado del servidor\n`$console` - Ver log de la consola\n`$info` - Información del servidor", inline=False)
        embed.add_field(name="🔒 Modo Solo Lectura", value="Este bot solo permite consultar información, no modificar el servidor", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def status(ctx):
    """Ver estado detallado del servidor actual"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    await ctx.send("🔍 Analizando estado del servidor...")
    
    status_data, message = await aternos.get_server_status_detailed()
    
    embed = discord.Embed(
        title=f"📊 Estado: {aternos.current_server['name']}",
        color=0x0099ff
    )
    
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    embed.add_field(name="ID", value=aternos.current_server['id'], inline=True)
    
    if status_data:
        # Determinar estado principal
        if status_data.get('server_online'):
            status_icon = "🟢"
            status_text = "En línea"
            color = 0x00ff00
        elif status_data.get('server_starting'):
            status_icon = "🟡"
            status_text = "Iniciando"
            color = 0xffaa00
        else:
            status_icon = "🔴"
            status_text = "Apagado"
            color = 0xff0000
        
        embed.color = color
        embed.add_field(name="Estado", value=f"{status_icon} {status_text}", inline=True)
        
        # Características disponibles
        features = []
        if status_data.get('has_console'):
            features.append("🎮 Consola disponible")
        if status_data.get('has_start_button'):
            features.append("▶️ Puede iniciar")
        if status_data.get('has_stop_button'):
            features.append("⏹️ Puede detener")
        
        if features:
            embed.add_field(name="Características", value="\n".join(features), inline=False)
        
        embed.add_field(name="Info Técnica", value=message, inline=False)
        
    else:
        embed.add_field(name="Error", value=message, inline=False)
        embed.color = 0xff0000
    
    await ctx.send(embed=embed)

@bot.command()
async def console(ctx):
    """Ver los últimos mensajes de la consola (solo lectura)"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    await ctx.send("📋 Obteniendo log de la consola...")
    
    log_data, message = await aternos.get_console_log()
    
    embed = discord.Embed(
        title="📋 Consola del Servidor",
        color=0x0099ff
    )
    
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    embed.add_field(name="Estado", value=message, inline=True)
    embed.add_field(name="Modo", value="🔒 Solo Lectura", inline=True)
    
    if log_data:
        if 'log' in log_data:
            # Si es JSON con log
            log_text = str(log_data['log'])[:1000]
            embed.add_field(name="Últimos mensajes", value=f"```{log_text}```", inline=False)
        elif 'html_log' in log_data:
            # Si es HTML, extraer texto útil
            html_log = log_data['html_log']
            # Limpiar HTML y mostrar parte del contenido
            clean_log = re.sub(r'<[^>]*>', '', html_log)[:500]
            embed.add_field(name="Log (HTML)", value=f"```{clean_log}```", inline=False)
        else:
            embed.add_field(name="Contenido", value=str(log_data)[:500], inline=False)
    else:
        embed.add_field(name="❌ Error", value="No se pudo obtener el log", inline=False)
    
    embed.set_footer(text="💡 Para ver más detalles, accede a la consola web de Aternos")
    
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx):
    """Información completa del servidor actual"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    await ctx.send("📊 Obteniendo información completa del servidor...")
    
    server_id = aternos.current_server['id']
    server_url = f'https://aternos.org/server/{server_id}'
    
    try:
        response = aternos.session.get(server_url)
        
        embed = discord.Embed(
            title=f"📊 Información: {aternos.current_server['name']}",
            color=0x0099ff
        )
        
        embed.add_field(name="ID", value=server_id, inline=True)
        embed.add_field(name="Nombre", value=aternos.current_server['name'], inline=True)
        embed.add_field(name="Software", value="Minecraft", inline=True)
        embed.add_field(name="Acceso", value="✅ OK" if response.status_code == 200 else f"❌ {response.status_code}", inline=True)
        
        if response.status_code == 200:
            html = response.text.lower()
            
            # Detectar características disponibles
            features = []
            if 'console' in html:
                features.append("🎮 Consola")
            if 'files' in html:
                features.append("📁 Archivos")
            if 'players' in html:
                features.append("👥 Jugadores")
            if 'plugins' in html:
                features.append("🔌 Plugins")
            if 'mods' in html:
                features.append("⚙️ Mods")
            
            embed.add_field(name="Características", value="\n".join(features) if features else "❌ Ninguna detectada", inline=False)
            
            # Buscar indicadores de estado
            status_indicators = []
            if 'online' in html:
                status_indicators.append("🟢 Online detectado")
            if 'offline' in html:
                status_indicators.append("🔴 Offline detectado")
            if 'starting' in html:
                status_indicators.append("🟡 Starting detectado")
            
            if status_indicators:
                embed.add_field(name="Estado Detectado", value="\n".join(status_indicators), inline=False)
        
        # Enlaces útiles
        links = f"[Panel del Servidor]({server_url})\n"
        links += f"[Consola Web]({server_url}/console)\n"
        links += f"[Archivos]({server_url}/files)"
        embed.add_field(name="Enlaces Útiles", value=links, inline=False)
        
        embed.set_footer(text="🔒 Bot en modo solo lectura - Sin modificaciones permitidas")
        
    except Exception as e:
        embed.add_field(name="❌ Error", value=str(e), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def servers(ctx):
    """Listar servidores disponibles"""
    if not aternos.logged_in:
        await ctx.send("❌ No conectado a Aternos")
        return
    
    if not aternos.servers:
        await ctx.send("❌ No se encontraron servidores")
        return
    
    embed = discord.Embed(
        title="📋 Servidores de Aternos",
        description=f"Encontrados: {len(aternos.servers)}",
        color=0x0099ff
    )
    
    for i, server in enumerate(aternos.servers, 1):
        name = server.get('displayname', server.get('name', f'Servidor {i}'))
        server_id = server.get('id', 'N/A')
        
        status_icon = "🎯" if aternos.current_server and aternos.current_server['id'] == server_id else "⚪"
        
        if server_id == '84jkIui0VIWl9vQ6':
            name = f"🔬 {name} (LabForkRecargado)"
        
        embed.add_field(
            name=f"{status_icon} {i}. {name}",
            value=f"**ID:** {server_id}",
            inline=False
        )
    
    embed.set_footer(text="🔒 Modo solo consulta - Sin modificaciones")
    
    await ctx.send(embed=embed)

@bot.command()
async def aternos_status(ctx):
    """Verificar estado de conexión con Aternos"""
    if aternos.logged_in:
        embed = discord.Embed(
            title="✅ Estado de Aternos",
            description="Conectado exitosamente",
            color=0x00ff00
        )
        
        embed.add_field(name="Servidores", value=f"{len(aternos.servers)} encontrado(s)", inline=True)
        embed.add_field(name="Servidor Actual", value=aternos.current_server['name'] if aternos.current_server else "Ninguno", inline=True)
        embed.add_field(name="Modo", value="🔒 Solo Lectura", inline=True)
        
    else:
        embed = discord.Embed(
            title="❌ Estado de Aternos", 
            description="No conectado",
            color=0xff0000
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def test(ctx, *args):
    """Comando de prueba"""
    respuesta = ' '.join(args) if args else "¡Comando de prueba funcionando!"
    await ctx.send(f"🧪 **Prueba:** {respuesta}")

@bot.command()
async def stats(ctx, player_name=None):
    """Ver estadísticas reales de un jugador con números específicos"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if not player_name:
        await ctx.send("❌ Debes especificar un nombre de jugador.\nEjemplo: `$stats TheHobbot`")
        return
    
    # Mensaje de carga
    loading_msg = await ctx.send(f"📊 Obteniendo estadísticas reales de **{player_name}**...\n⏳ *Esto puede tomar unos segundos...*")
    
    # Obtener estadísticas con números reales
    stats_data, message = await aternos.get_player_stats_with_real_numbers(player_name)
    
    embed = discord.Embed(
        title=f"📊 Estadísticas: {player_name}",
        color=0x00ff00
    )
    
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    embed.add_field(name="Jugador", value=player_name, inline=True)
    embed.add_field(name="Estado", value="✅ Comandos ejecutados", inline=True)
    
    if stats_data:
        # Mostrar estadísticas principales con números
        main_stats = []
        
        # Bloques destruidos
        bloques_data = stats_data.get('bloques_destruidos', {})
        if bloques_data.get('real_data'):
            # Extraer número de bloques
            bloques_text = bloques_data['real_data']
            numeros = re.findall(r'\d+', bloques_text)
            if numeros:
                total_bloques = sum(int(n) for n in numeros)
                main_stats.append(f"⛏️ **Bloques Destruidos:** {total_bloques:,}")
            else:
                main_stats.append(f"⛏️ **Bloques Destruidos:** {bloques_text[:50]}")
        else:
            main_stats.append(f"⛏️ **Bloques Destruidos:** ❌ No disponible")
        
        # Muertes
        muertes_data = stats_data.get('muertes', {})
        if muertes_data.get('real_data'):
            muertes_text = muertes_data['real_data']
            numeros = re.findall(r'\d+', muertes_text)
            if numeros:
                main_stats.append(f"💀 **Muertes:** {numeros[0]}")
            else:
                main_stats.append(f"💀 **Muertes:** {muertes_text[:50]}")
        else:
            main_stats.append(f"💀 **Muertes:** ❌ No disponible")
        
        # Tiempo jugado
        tiempo_data = stats_data.get('tiempo_jugado', {})
        if tiempo_data.get('real_data'):
            tiempo_text = tiempo_data['real_data']
            numeros = re.findall(r'\d+', tiempo_text)
            if numeros:
                ticks = int(numeros[0])
                horas = ticks / 72000  # 1 hora = 72,000 ticks
                main_stats.append(f"⏰ **Tiempo Jugado:** {horas:.1f} horas ({ticks:,} ticks)")
            else:
                main_stats.append(f"⏰ **Tiempo Jugado:** {tiempo_text[:50]}")
        else:
            main_stats.append(f"⏰ **Tiempo Jugado:** ❌ No disponible")
        
        # Mostrar estadísticas principales
        embed.add_field(
            name="📊 Estadísticas Principales",
            value="\n".join(main_stats),
            inline=False
        )
        
        # Información adicional con números
        additional_info = []
        
        # Vida
        vida_data = stats_results.get('vida', {})
        if vida_data.get('real_data'):
            vida_text = vida_data['real_data']
            numeros = re.findall(r'\d+\.?\d*', vida_text)
            if numeros:
                additional_info.append(f"❤️ **Vida:** {numeros[0]}/20")
            else:
                additional_info.append(f"❤️ **Vida:** {vida_text[:30]}")
        
        # Nivel XP
        xp_data = stats_results.get('nivel_xp', {})
        if xp_data.get('real_data'):
            xp_text = xp_data['real_data']
            numeros = re.findall(r'\d+', xp_text)
            if numeros:
                additional_info.append(f"⭐ **Nivel XP:** {numeros[0]}")
            else:
                additional_info.append(f"⭐ **Nivel XP:** {xp_text[:30]}")
        
        # Posición
        pos_data = stats_results.get('posicion', {})
        if pos_data.get('real_data'):
            pos_text = pos_data['real_data']
            numeros = re.findall(r'-?\d+\.?\d*', pos_text)
            if len(numeros) >= 3:
                x, y, z = numeros[0], numeros[1], numeros[2]
                additional_info.append(f"📍 **Posición:** X:{x} Y:{y} Z:{z}")
            else:
                additional_info.append(f"📍 **Posición:** {pos_text[:50]}")
        
        # Dimensión
        dim_data = stats_results.get('dimension', {})
        if dim_data.get('real_data'):
            dim_text = dim_data['real_data'].lower()
            if 'overworld' in dim_text:
                additional_info.append(f"🌍 **Dimensión:** 🌱 Overworld")
            elif 'nether' in dim_text:
                additional_info.append(f"🌍 **Dimensión:** 🔥 Nether")
            elif 'end' in dim_text:
                additional_info.append(f"🌍 **Dimensión:** 🌌 End")
            else:
                additional_info.append(f"🌍 **Dimensión:** {dim_text[:30]}")
        
        if additional_info:
            embed.add_field(
                name="ℹ️ Información Adicional",
                value="\n".join(additional_info),
                inline=False
            )
        
        # Mostrar respuestas raw para debug
        raw_responses = []
        for stat_name, data in stats_results.items():
            if data.get('real_data'):
                raw_responses.append(f"**{stat_name}:** {data['real_data'][:80]}")
        
        if raw_responses:
            embed.add_field(
                name="🔧 Respuestas Raw (Debug)",
                value="\n".join(raw_responses[:3]),
                inline=False
            )
    
    else:
        embed.add_field(
            name="❌ Error",
            value="No se pudieron obtener las estadísticas",
            inline=False
        )
        embed.color = 0xff0000
    
    # Enlaces útiles
    server_id = aternos.current_server['id']
    embed.add_field(
        name="🔗 Ver en Tiempo Real",
        value=f"[Consola Web](https://aternos.org/server/{server_id}/console) - Aquí puedes ver las respuestas completas",
        inline=False
    )
    
    embed.set_footer(text="📊 Intentando capturar respuestas reales del servidor")
    
    # Actualizar el mensaje de carga
    await loading_msg.edit(content="", embed=embed)

# Reemplazar el comando anterior

@bot.command()
async def player_data(ctx, player_name=None):
    """Obtener datos específicos de un jugador ejecutando comandos directamente"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if not player_name:
        await ctx.send("❌ Debes especificar un nombre de jugador.\nEjemplo: `$player_data TheHobbot`")
        return
    
    loading_msg = await ctx.send(f"🔍 Obteniendo datos de **{player_name}**...")
    
    # Comandos específicos para datos esenciales
    essential_commands = {
        'Posición': f'data get entity {player_name} Pos',
        'Vida': f'data get entity {player_name} Health',
        'Nivel XP': f'data get entity {player_name} XpLevel',
        'Dimensión': f'data get entity {player_name} Dimension',
        'Modo de Juego': f'data get entity {player_name} playerGameType'
    }
    
    results = {}
    
    for data_name, command in essential_commands.items():
        success, response = await aternos.send_console_command(command)
        results[data_name] = {
            'success': success,
            'response': response
        }
        await asyncio.sleep(0.3)  # Pausa entre comandos
    
    embed = discord.Embed(
        title=f"🔍 Datos: {player_name}",
        color=0x0099ff
    )
    
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    embed.add_field(name="Jugador", value=player_name, inline=True)
    embed.add_field(name="Comandos", value=f"{len(results)} ejecutados", inline=True)
    
    # Mostrar resultados
    for data_name, result in results.items():
        status_icon = "✅" if result['success'] else "❌"
        response = result.get('response', 'Sin respuesta')
        
        # Acortar respuesta si es muy larga
        if isinstance(response, str) and len(response) > 100:
            response = response[:100] + "..."
        
        embed.add_field(
            name=f"{status_icon} {data_name}",
            value=f"```{response}```",
            inline=False
        )
    
    await loading_msg.edit(content="", embed=embed)

@bot.command()
async def player_info(ctx, player_name=None):
    """Obtener información real del jugador capturando respuestas del servidor"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if not player_name:
        await ctx.send("❌ Debes especificar un nombre de jugador.\nEjemplo: `$player_info TheHobbot`")
        return
    
    loading_msg = await ctx.send(f"🔍 Capturando información real de **{player_name}**...\n⏳ *Esto puede tomar hasta 40 segundos...*")
    
    # Obtener información con captura real
    info_data, message = await aternos.get_player_info_with_real_capture(player_name)
    
    embed = discord.Embed(
        title=f"🔍 Información Real: {player_name}",
        color=0x00ff00
    )
    
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    embed.add_field(name="Jugador", value=player_name, inline=True)
    embed.add_field(name="Estado", value="✅ Captura completada", inline=True)
    
    if info_data:
        # Procesar información capturada
        captured_info = []
        
        # Salud
        health_data = info_data.get('health', {})
        if health_data.get('real_data'):
            health_text = health_data['real_data']
            # Extraer número de la respuesta
            numbers = re.findall(r'\d+\.?\d*', health_text)
            if numbers:
                captured_info.append(f"❤️ **Vida:** {numbers[0]}/20")
            else:
                captured_info.append(f"❤️ **Vida:** {health_text[:50]}")
        else:
            captured_info.append(f"❤️ **Vida:** ❌ No capturada")
        
        # Posición
        pos_data = info_data.get('position', {})
        if pos_data.get('real_data'):
            pos_text = pos_data['real_data']
            # Buscar coordenadas [X, Y, Z]
            numbers = re.findall(r'-?\d+\.?\d*', pos_text)
            if len(numbers) >= 3:
                x, y, z = numbers[0], numbers[1], numbers[2]
                captured_info.append(f"📍 **Posición:** X:{x} Y:{y} Z:{z}")
            else:
                captured_info.append(f"📍 **Posición:** {pos_text[:50]}")
        else:
            captured_info.append(f"📍 **Posición:** ❌ No capturada")
        
        # Nivel XP
        xp_data = info_data.get('xp_level', {})
        if xp_data.get('real_data'):
            xp_text = xp_data['real_data']
            numbers = re.findall(r'\d+', xp_text)
            if numbers:
                captured_info.append(f"⭐ **Nivel XP:** {numbers[0]}")
            else:
                captured_info.append(f"⭐ **Nivel XP:** {xp_text[:50]}")
        else:
            captured_info.append(f"⭐ **Nivel XP:** ❌ No capturada")
        
        # Dimensión
        dim_data = info_data.get('dimension', {})
        if dim_data.get('real_data'):
            dim_text = dim_data['real_data'].lower()
            if 'overworld' in dim_text:
                captured_info.append(f"🌍 **Dimensión:** 🌱 Overworld")
            elif 'nether' in dim_text:
                captured_info.append(f"🌍 **Dimensión:** 🔥 Nether")
            elif 'end' in dim_text:
                captured_info.append(f"🌍 **Dimensión:** 🌌 End")
            else:
                captured_info.append(f"🌍 **Dimensión:** {dim_text[:30]}")
        else:
            captured_info.append(f"🌍 **Dimensión:** ❌ No capturada")
        
        # Modo de juego
        gamemode_data = info_data.get('gamemode', {})
        if gamemode_data.get('real_data'):
            gm_text = gamemode_data['real_data'].lower()
            if '0' in gm_text or 'survival' in gm_text:
                captured_info.append(f"🎮 **Modo:** Supervivencia")
            elif '1' in gm_text or 'creative' in gm_text:
                captured_info.append(f"🎮 **Modo:** Creativo")
            elif '2' in gm_text or 'adventure' in gm_text:
                captured_info.append(f"🎮 **Modo:** Aventura")
            elif '3' in gm_text or 'spectator' in gm_text:
                captured_info.append(f"🎮 **Modo:** Espectador")
            else:
                captured_info.append(f"🎮 **Modo:** {gm_text[:20]}")
        else:
            captured_info.append(f"🎮 **Modo:** ❌ No capturado")
        
        # Mostrar información capturada
        embed.add_field(
            name="📊 Datos Capturados",
            value="\n".join(captured_info),
            inline=False
        )
        
        # Mostrar respuestas raw capturadas
        raw_responses = []
        for info_name, data in info_data.items():
            if data.get('real_data'):
                raw_responses.append(f"**{info_name}:** {data['real_data'][:60]}")
        
        if raw_responses:
            embed.add_field(
                name="🔧 Respuestas Capturadas",
                value="\n".join(raw_responses[:3]),
                inline=False
            )
        
        # Estadísticas de captura
        captured_count = sum(1 for data in info_data.values() if data.get('real_data'))
        total_count = len(info_data)
        
        embed.add_field(
            name="📈 Estadísticas de Captura",
            value=f"✅ Capturadas: {captured_count}/{total_count}\n📊 Éxito: {(captured_count/total_count)*100:.1f}%",
            inline=True
        )
    
    else:
        embed.add_field(
            name="❌ Error",
            value="No se pudieron capturar los datos",
            inline=False
        )
        embed.color = 0xff0000
    
    server_id = aternos.current_server['id']
    embed.add_field(
        name="🔗 Consola Web",
        value=f"[Ver Consola](https://aternos.org/server/{server_id}/console)",
        inline=True
    )
    
    embed.set_footer(text="🎯 Datos capturados directamente de las respuestas del servidor")
    
    # Actualizar el mensaje de carga
    await loading_msg.edit(content="", embed=embed)

@bot.command()
async def test_capture(ctx, player_name=None):
    """Probar captura de una sola respuesta"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if not player_name:
        player_name = "TheHobbot"  # Default
    
    command = f"data get entity {player_name} Health"
    
    loading_msg = await ctx.send(f"🧪 Probando captura de respuesta para comando: `/{command}`")
    
    # Probar captura
    success, response, real_data = await aternos.send_command_with_response_capture(command, timeout=10)
    
    embed = discord.Embed(
        title="🧪 Prueba de Captura",
        color=0x00ff00 if real_data else 0xffaa00
    )
    
    embed.add_field(name="Comando", value=f"`/{command}`", inline=False)
    embed.add_field(name="Envío", value="✅ Exitoso" if success else "❌ Error", inline=True)
    embed.add_field(name="Captura", value="✅ Exitosa" if real_data else "❌ Sin captura", inline=True)
    
    if real_data:
        embed.add_field(name="Respuesta Capturada", value=f"```{real_data}```", inline=False)
        
        # Extraer datos específicos
        numbers = re.findall(r'\d+\.?\d*', real_data)
        if numbers:
            embed.add_field(name="Datos Extraídos", value=f"Vida: {numbers[0]}/20", inline=True)
    else:
        embed.add_field(name="Estado", value=response, inline=False)
    
    embed.add_field(name="💡 Resultado", value="✅ ¡Captura funcionando!" if real_data else "⚠️ Revisar configuración", inline=False)
    
    await loading_msg.edit(content="", embed=embed)

# Agregar estos comandos antes de bot.run(secretos.TOKEN)

@bot.command()
async def debug_capture(ctx, player_name=None):
    """Comando para debug detallado de captura"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if not player_name:
        player_name = "TheHobbot"  # Default
    
    command = f"data get entity {player_name} Health"
    
    await ctx.send(f"🧪 **INICIANDO DEBUG DETALLADO**\n📤 Comando: `/{command}`\n🔍 Revisa la consola del bot para ver el debug completo...")
    
    # Ejecutar con debug detallado
    success, response, captured_data = await aternos.send_command_and_capture_response_debug(command, wait_time=6)
    
    embed = discord.Embed(
        title="🧪 Debug de Captura Completo",
        color=0x00ff00 if captured_data else 0xffaa00
    )
    
    embed.add_field(name="Comando", value=f"`/{command}`", inline=False)
    embed.add_field(name="Envío", value="✅ Exitoso" if success else "❌ Error", inline=True)
    embed.add_field(name="Captura", value="✅ Exitosa" if captured_data else "❌ Sin captura", inline=True)
    
    if captured_data:
        embed.add_field(
            name="🎯 Datos Capturados",
            value=f"```{captured_data}```",
            inline=False
        )
        
        # Extraer número de vida
        numbers = re.findall(r'\d+\.?\d*', captured_data)
        if numbers:
            embed.add_field(
                name="💖 Vida Detectada",
                value=f"**{numbers[0]}/20 corazones**",
                inline=True
            )
    else:
        embed.add_field(
            name="📝 Respuesta del Sistema",
            value=response,
            inline=False
        )
    
    embed.add_field(
        name="🔍 Información de Debug",
        value="Revisa la consola del bot para ver:\n• Estado inicial de la consola\n• Proceso de envío del comando\n• Nuevas líneas detectadas\n• Análisis de respuestas",
        inline=False
    )
    
    embed.set_footer(text="🧪 Debug completo - Revisa la consola del bot para detalles")
    
    await ctx.send(embed=embed)

@bot.command()
async def monitor_console(ctx, duration=10):
    """Monitorear la consola en tiempo real por X segundos"""
    if not aternos.current_server:
        await ctx.send("❌ No hay servidor seleccionado. Usa `$labfork` primero")
        return
    
    if duration > 30:
        duration = 30  # Máximo 30 segundos
    
    loading_msg = await ctx.send(f"👀 Monitoreando consola por {duration} segundos...")
    
    print(f"\n🔍 INICIANDO MONITOREO DE CONSOLA POR {duration} SEGUNDOS")
    print("="*60)
    
    # Capturar estado inicial
    initial_console = await aternos.get_live_console_data()
    initial_lines = aternos.extract_lines_from_console(initial_console)
    
    print(f"📊 Estado inicial: {len(initial_lines)} líneas")
    
    new_lines_found = []
    
    for second in range(duration):
        print(f"\n⏰ Segundo {second + 1}/{duration}")
        await asyncio.sleep(1)
        
        current_console = await aternos.get_live_console_data()
        current_lines = aternos.extract_lines_from_console(current_console)
        
        # Buscar nuevas líneas
        for line in current_lines:
            if line not in initial_lines and line not in [nl['line'] for nl in new_lines_found]:
                new_lines_found.append({
                    'second': second + 1,
                    'line': line
                })
                print(f"🆕 NUEVA LÍNEA: {line}")
    
    print(f"\n📊 RESUMEN DEL MONITOREO:")
    print(f"   Duración: {duration} segundos")
    print(f"   Nuevas líneas: {len(new_lines_found)}")
    
    # Crear embed con resultados
    embed = discord.Embed(
        title="👀 Monitoreo de Consola Completado",
        color=0x00ff00 if new_lines_found else 0xffaa00
    )
    
    embed.add_field(name="Duración", value=f"{duration} segundos", inline=True)
    embed.add_field(name="Nuevas Líneas", value=f"{len(new_lines_found)} encontradas", inline=True)
    embed.add_field(name="Servidor", value=aternos.current_server['name'], inline=True)
    
    if new_lines_found:
        # Mostrar últimas nuevas líneas
        recent_lines = []
        for item in new_lines_found[-5:]:  # Últimas 5
            recent_lines.append(f"[{item['second']}s] {item['line'][:80]}")
        
        embed.add_field(
            name="🆕 Últimas Líneas Detectadas",
            value="```" + "\n".join(recent_lines) + "```",
            inline=False
        )
    else:
        embed.add_field(
            name="📝 Resultado",
            value="No se detectaron nuevas líneas durante el monitoreo",
            inline=False
        )
    
    embed.add_field(
        name="💡 Sugerencia",
        value="Ejecuta un comando manualmente en la consola web mientras usas este comando para ver cómo aparecen las respuestas",
        inline=False
    )
    
    await loading_msg.edit(content="", embed=embed)

bot.run(secretos.TOKEN)