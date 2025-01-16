from importlib.metadata import metadata

import spade
import asyncio
from spade.behaviour import CyclicBehaviour
import heapq
import math


class FiremanAgent(spade.agent.Agent):

    async def setup(self):

        self.location = None
        self.mobility = 1
        self.environment = None
        self.id = 5
        self.fire_coords = []
        self.available_exits = []
        self.state = None
        self.best_entry = None
        self.fireman_called = False
        self.requester_position = None

        print(f"Agente de Segurança {self.id} configurado e aguardando para ser inicializado")

        #comportamentos e comunicaçao
        # bombeiro recebe pedido de socorro dos segurancas - fire_coords e saidas nao comprometidas
        # bombeiro escolhe entrar pela saida mais proxima das fire_coords

        loop_bombeiro = self.LoopBombeiro()
        self.add_behaviour(loop_bombeiro)


    async def set_attributes(self, location, environment):
        self.location = location
        self.environment = environment
        self.environment.update_agent_position(None, self.location, self.id)
        self.environment.display_map()

    async def move_to_building(self):
        #print(f"{self.jid}: Deslocando-se para o prédio...")
        await asyncio.sleep(40)  # Simula o deslocamento de 40 segundos
        #print(f"{self.jid}: Chegou ao prédio.")

    def dijkstra_step(self, start, goal,flag=0):
        distances = {start: 0}
        previous_nodes = {start: None}
        priority_queue = [(0, start)]

        while priority_queue:
            current_distance, current_position = heapq.heappop(priority_queue)


            if current_position == goal:
                path = []
                while current_position is not None:
                    path.append(current_position)
                    current_position = previous_nodes[current_position]
                path.reverse()

                return path[1:]  # Retorna o caminho sem a posição inicial

            if flag == 1:
                for neighbor in self.get_neighbors(current_position,1):

                    if self.environment.is_transitable(neighbor, ignore_agents=True):
                        distance = current_distance + 1
                        if neighbor not in distances or distance < distances[neighbor]:
                            distances[neighbor] = distance
                            previous_nodes[neighbor] = current_position
                            heapq.heappush(priority_queue, (distance, neighbor))
            elif flag == 0:
                for neighbor in self.get_neighbors(current_position, 0):

                    if self.environment.is_transitable(neighbor, ignore_agents=False):
                        distance = current_distance + 1
                        if neighbor not in distances or distance < distances[neighbor]:
                            distances[neighbor] = distance
                            previous_nodes[neighbor] = current_position
                            heapq.heappush(priority_queue, (distance, neighbor))


        return None

    def get_neighbors(self, position, flag=0):
        x, y = position
        neighbors = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_x, new_y = x + dx, y + dy

            if flag == 1:
                if self.environment.is_transitable((new_x, new_y),1):
                    neighbors.append((new_x, new_y))
            elif flag == 0:
                if self.environment.is_transitable((new_x, new_y),0):
                    neighbors.append((new_x, new_y))
        return neighbors

    def find_occupants_perimeter(self, position):
        rows, cols = len(self.environment.building_map), len(self.environment.building_map[0])
        occupants_found = []  # List to store the JIDs of occupants found

        # Iterate through a 3x3 grid centered on the position
        for dx in range(-2, 3):  # Offsets: -1, 0, 1 for rows
            for dy in range(-2, 3):  # Offsets: -1, 0, 1 for columns
                if dx == 0 and dy == 0:
                    continue  # Skip the center position (security's own position)

                neighbor = (position[0] + dx, position[1] + dy)

                # Check if the neighbor is within the map bounds
                if 0 <= neighbor[0] < rows and 0 <= neighbor[1] < cols:
                    # Check if the cell contains an occupant (2 or 3)
                    if self.environment.building_map[neighbor[0]][neighbor[1]] in {2, 3}:
                        jid_at_pos = self.environment.get_agent_jid_at_position(neighbor)
                        if jid_at_pos:  # Ensure JID exists before adding
                            occupants_found.append(jid_at_pos)

        return occupants_found

    def choose_entry(self): # depois de atualizadas as self.fire_coords e available_exits
        min_distance = 10000
        entry_exit = None


        for exit in self.available_exits:
            for fire in self.fire_coords:
                path = self.dijkstra_step(exit, fire, 1)
                if path and len(path) < min_distance:
                    entry_exit = exit
                    min_distance = len(path)

        if entry_exit:
            return entry_exit
        else:
            #print("Nao é possivel entrar no edificio")
            return None

    # assim que escolhe a entrada, desloca-se até às coordenadas com fogo - tem de calcular o caminhos mais proximo
    def move_to_fire(self, best_entry):
        min_distance = 1000000
        best_path = None
        for fire in self.fire_coords:
            path = self.dijkstra_step(best_entry,fire,  1) # conta com o fogo como transitavel
            if path and len(path) < min_distance:
                min_distance = len(path)
                best_path = path

        if best_path:
            return best_path





    def extinguish_fire(self):
        x, y = self.location
        directions = [
            (0, 1),  # Direita
            (0, -1),  # Esquerda
            (1, 0),  # Baixo
            (-1, 0),  # Cima
            (1, 1),
            (-1, 1),
            (1, -1),
            (-1, -1),
        ]

        # Verificar cada direção adjacente
        for dx, dy in directions:
            new_x, new_y = x + dx, y + dy
            if (0 <= new_x < len(self.environment.building_map)) and (
                    0 <= new_y < len(self.environment.building_map[0])):
                if self.environment.building_map[new_x][new_y] == 4:
                    self.environment.building_map[new_x][new_y] = 'W'

    def get_best_exit(self):
        exits = self.environment.exits
        min_distance = 100000000
        best_exit = None
        for exit in exits:
            path = self.dijkstra_step(self.requester_position, exit)
            #print(f"O path é {path} e a saída é {exit}")
            if path:
                if len(path) < min_distance:
                    min_distance = len(path)
                    best_exit = exit

        return best_exit




    class LoopBombeiro (spade.behaviour.CyclicBehaviour):
        async def run(self):

            if not self.agent.state:
                receber_informacoes = self.agent.ReceberInformacoes()
                self.agent.add_behaviour(receber_informacoes)



            if self.agent.state == 'Evacuating':





                # fireman já guardou como atributos as coordenadas de fogo e as saidas disposiveis
                self.agent.best_entry = self.agent.choose_entry()
                self.agent.environment.update_agent_position(self.agent.location, self.agent.best_entry, self.agent.id, self.agent.jid)
                self.agent.location = self.agent.best_entry

                self.agent.state = 'Ir ate ao Fogo'

            if self.agent.state == 'Ir ate ao Fogo':

                entry_path = self.agent.move_to_fire(self.agent.location)

                if entry_path:
                    #print("ELE TEM PATH PARA O FOGO:", entry_path)
                    next_position = entry_path.pop(0)
                    #print("next_position", next_position)


                    if self.agent.environment.is_transitable(next_position, ignore_agents= False):
                        self.agent.environment.update_agent_position(self.agent.location, next_position, self.agent.id, self.agent.jid)
                        self.agent.location = next_position
                    else:
                        self.agent.state = 'Apagando o Fogo'



            if self.agent.state == 'Apagando o Fogo':
                #("Entrei AQui!!")
                self.agent.extinguish_fire()

                self.agent.state = 'Ir ate ao Fogo'

            if self.agent.state == 'Helping':
                entry_path = self.agent.dijkstra_step(self.agent.location, self.agent.requester_position)
                if entry_path:

                    next_position = entry_path.pop(0)
                    if(self.agent.environment.building_map[next_position[0]][next_position[1]] == 2):
                        occupant = self.agent.environment.get_agent_jid_at_position(next_position)
                        resposta = spade.message.Message(to=str(occupant))
                        resposta.body = 'Mandar saida'
                        resposta.metadata = {"saida": str(self.agent.get_best_exit())}
                        await self.send(resposta)
                        print(f"{occupant} recebeu a saida mais proxima do {self.agent.jid}.")
                        self.agent.state = 'Ir ate ao Fogo'


                    if self.agent.environment.is_transitable(next_position, ignore_agents= False):
                        self.agent.environment.update_agent_position(self.agent.location, next_position, self.agent.id, self.agent.jid)
                        self.agent.location = next_position
                    else:
                        self.agent.state = 'Apagando o Fogo'

            if self.agent.state:
              await asyncio.sleep(3)



    class ReceberInformacoes(spade.behaviour.CyclicBehaviour):

        async def run(self):
            # Receber as coordenadas e as saidas disponiveis
            message = await self.receive()
            if message:


                if message.body == 'Socorro':
                    #print("Bombeiro recebeu pedido de socorro")

                    await self.agent.move_to_building()

                    self.agent.fireman_called = True


                if self.agent.fireman_called and ' at ' in message.body:

                    self.agent.fire_coords = eval(message.metadata.get("fire_coords"))
                    self.agent.available_exits = eval(message.metadata.get("available_exits"))

                    if not self.agent.state:
                        self.agent.state = 'Evacuating'

                if message.body == 'Ajuda':
                    self.agent.requester_position = eval(message.metadata.get("position", "(-1, -1)"))
                    self.agent.state = 'Helping'



    # salvar pessoas - pensar melhor
    class AjudaOcupantes(spade.behaviour.OneShotBehaviour):
        def __init__(self, ocupante):
            super().__init__()
            self.ocupante = ocupante

        async def run(self):
            msg = spade.message.Message(to=str(self.ocupante))
            msg.body = 'Saida bombeiro'
            msg.metadata = {"saida": "aaa"}
            await self.send(msg)




