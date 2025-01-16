import spade
import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour,CyclicBehaviour
from spade.message import Message
from environment import Environment

class BuildingManagement(Agent):
    def __init__(self, jid, password, occupants_jids, security_jids,firemen_jids, environment):
        super().__init__(jid, password)
        self.alarm = False
        self.occupants_jids = occupants_jids  # Lista de JIDs dos ocupantes
        self.security_jids = security_jids
        self.firemen_jids = firemen_jids
        self.environment = environment





    class ChangeAlarmBehaviour(OneShotBehaviour):
        async def run(self):
            self.agent.alarm = not self.agent.alarm
            status = "activated" if self.agent.alarm else "deactivated"
            print(f"Alarm {status}")

            # Enviar mensagem aos ocupantes sobre o estado do alarme
            for occupant_jid in self.agent.occupants_jids:
                msg = Message(to=occupant_jid)
                msg.body = "alarm_activated" if self.agent.alarm else "alarm_deactivated"
                await self.send(msg)
                #print(f"Mensagem de alarme enviada para {occupant_jid}.")

            '''
            # Enviar mensagem aos ocupantes sobre o estado do alarme
            msg = Message(to="occupant@localhost")  # Modificar o JID conforme necessário
            msg.body = "alarm_activated" if self.agent.alarm else "alarm_deactivated"
            await self.send(msg)
            print("Mensagem de alarme enviada para os ocupantes.")
            '''

    class AlertSecurityBehaviour(CyclicBehaviour):
        async def run(self):
            if not self.agent.alarm:
                print("Alarm is deactivated. No alerts being sent.")
                self.agent.stop()
                self.agent.environment.end = True
                await asyncio.sleep(5)  # Wait before checking again
                return

            fire_coordinates = []
            # Check the environment for fire
            for i, row in enumerate(self.agent.environment.building_map):
                for j, cell in enumerate(row):
                    if cell == 4:  # Fire is represented as 4
                        fire_coordinates.append((i, j))

            if fire_coordinates:
                fire_coords_str = str(fire_coordinates)
                #print(f"Detected fire at: {fire_coordinates}. Sending alerts to security officers.")

                # Send fire coordinates to all security officers
                for security_jid in self.agent.security_jids:
                    #print("security jid:" ,type(security_jid))
                    msg = Message(to=security_jid)
                    msg.body = f"alarm_activated fire coordinates at {fire_coords_str}"
                    msg.metadata = {"performative": "inform"}
                    await self.send(msg)
                    print(f"Alert sent to {security_jid} with coordinates: {fire_coordinates}")

                #print("Lista firemen: ", self.agent.firemen_jids)
                for firemen_jid in self.agent.firemen_jids:

                    msg = Message(to=firemen_jid)
                    msg.body = "alarm_activated at fire coordinates"
                    msg.metadata = {"fire_coords": f"{fire_coords_str}", "available_exits": f"{self.agent.environment.exits}"}
                    await self.send(msg)
                    #print("mensagem inventada por sara: ", msg)
                    print(f"Alert sent to {firemen_jid} with coordinates: {fire_coordinates}")
            else:
                print("No fire detected in the building.")
                change_alarm_behaviour = self.agent.ChangeAlarmBehaviour()
                self.agent.add_behaviour(change_alarm_behaviour)

            await asyncio.sleep(3)  # Repeat every 5 seconds



    async def setup(self):
        print(f"{self.jid} iniciado. Alarme desativado.")


    async def change_alarm(self):
        change_alarm_behaviour = self.ChangeAlarmBehaviour()
        self.add_behaviour(change_alarm_behaviour)
        a = self.AlertSecurityBehaviour()
        self.add_behaviour(a)






