import asyncio
from environment import Environment
from OccupantAgent import OccupantAgent
from BuildingManagement import BuildingManagement
from SecurityAgent import SecurityAgent
from FiremanAgent import FiremanAgent
from fire import Fire
from interface import Interface
import time




async def run_sim(simulation_number):

    environment = Environment()
    if not environment.end:
        start_time = time.time()
        # Lista de JIDs dos ocupantes
        occupants_jids = []
        fireman_jids = []
        security_jids = []

        # Criar e inicializar múltiplos agentes ocupantes
        num_agents = 5  # Número de agentes ocupantes

        occupants = []

        for i in range(5):
            jid = f"occupant{i}@localhost"
            occupant = OccupantAgent(jid, "password")
            await occupant.start()
            await occupant.set_attributes(environment.get_random_location(), mobility=1, environment=environment, knowlegde= 1)

            # Adicionar o JID do ocupante à lista de JIDs
            occupants_jids.append(jid)
            occupants.append(occupant)

        for i in range(6,10):
            jid = f"occupant{i}@localhost"
            occupant = OccupantAgent(jid, "password")
            await occupant.start()
            await occupant.set_attributes(environment.get_random_location(), mobility=1, environment=environment, knowlegde= 2)

            # Adicionar o JID do ocupante à lista de JIDs
            occupants_jids.append(jid)
            occupants.append(occupant)
        #Esperar para que todos os agentes estejam criados e inicializados
        await asyncio.sleep(2)

        num_fireman_agents = 1  # Numero de bombeiros
        fireman_agents = []

        for i in range(num_fireman_agents):
            jid = f"fireman{i}@localhost"

            fireman_agent = FiremanAgent(jid, "password")

            await fireman_agent.start()
            await fireman_agent.set_attributes((0, 0), environment)

            fireman_jids.append(jid)
            fireman_agents.append(fireman_agent)

        num_security_agents = 2 # Numero de agentes de segurança

        security_agents = []


        for i in range(num_security_agents):
            jid = f"security{i}@localhost"


            security_agent = SecurityAgent(jid, "password")

            await security_agent.start()
            await security_agent.set_attributes(environment.get_random_location(), environment)

            security_jids.append(jid)
            security_agents.append(security_agent)

        for security_agent in security_agents:

            security_agent.fireman_agents = fireman_jids
            security_agent.occupant_agents = occupants_jids

        interface = Interface(environment)
        visualization_task = asyncio.create_task(interface.run())



        # Criar e inicializar o sistema de gestão predial com a lista de JIDs
        building_management = BuildingManagement("building@localhost", "password", occupants_jids, security_jids,fireman_jids, environment)

        #Começar a logica de navegaçao -> Que e equivalente a um .start()?

        for occupant in occupants:
            navigation_behaviour = occupant.NavigationBehaviour()
            occupant.add_behaviour(navigation_behaviour)

        """
        for occupant in occupants:
            await occupant.start()
    
        for security in security_agents:
            await security.start()
    
        for fireman_agent in fireman_agents:
            await fireman_agent.start()
        """
        await building_management.start()

        # Iniciar o sistema de incêndio
        fire_system = Fire(environment, building_management, spread_interval=20)

        print("✅ Sistema de incêndio inicializado.")
        fire_task = asyncio.create_task(fire_system.continuous_spread())
        print("🔥 Tarefa de propagação do fogo iniciada.")

        # Verificar se todos os ocupantes evacuaram
        try:
            while building_management: ## Da verdadeiro se houver ainda ocupantes por evacuar

                await visualization_task


            print("🏃 Todos os agentes evacuaram o edifício! Encerrar o programa...")

        except KeyboardInterrupt:
            print("Encerrar o programa...")

        finally:
            fire_task.cancel()  # Cancela a tarefa de propagação do fogo
            for occupant in occupants:
                await occupant.stop()
            for security_agent in security_agents:
                await security_agent.stop()
            await building_management.stop()

        end_time = time.time()
        # Contar mortes e sobreviventes
        dead_count = sum(occupant.dead for occupant in occupants)
        survived_count = sum(not occupant.dead for occupant in occupants)
        print(f"⚡ Resultados da simulação {simulation_number}: {survived_count} sobreviveram, {dead_count} morreram.")

        for occupant in occupants:
            await occupant.stop()
        return dead_count, survived_count, end_time - start_time




async def main():
    num_simulations = 3 # Número de simulações a executar
    total_dead = 0
    total_survived = 0
    times =[]

    for i in range(1, num_simulations + 1):
        dead, survived, total_time = await run_sim(i)
        total_dead += dead
        total_survived += survived
        times.append(total_time)

    print("\n📊 Estatísticas finais:")
    print(f"🔴 Total de mortes: {total_dead}")
    print(f"🟢 Total de sobreviventes: {total_survived}")
    print(f"📈 Taxa de sobrevivência: {total_survived / (total_dead + total_survived):.2%}")
    print(f"📉 Taxa de mortalidade: {total_dead / (total_dead + total_survived):.2%}")
    print(f" Media dos tempo de simulacao: ", sum(times) / len(times))


if __name__ == "__main__":
    asyncio.run(main())