from app.models.lab import ClabConfig, Exercise, ExerciseCheck, LabDefinition, LabFormula, LabCredentials

STATIC_ROUTING_PATH = "/home/deploy/labs/networking001/lab-rutas_estaticas"

ROUTERS = ["r1", "r2", "r3"]

STATIC_ROUTING_EXERCISES: list[Exercise] = [
    Exercise(
        id="step-1",
        number=1,
        title="Verificar tabla de ruteo vacía",
        description=(
            'Efectuar en cualquiera de los routers el comando "show ip route" para verificar '
            "la tabla de ruteo del equipo. Dado que no existe ninguna dirección IP configurada, "
            "este comando no mostrará ninguna entrada en la tabla de ruteo."
        ),
        checks=[
            ExerciseCheck(
                devices=ROUTERS,
                command=r"^show\s+ip\s+route$",
                output_excludes=["10.10.10.", "10.20.20.", "10.30.30.", "10.1.2.", "10.2.3."],
                description="Run show ip route on any router before configuring LAN IPs",
            )
        ],
    ),
    Exercise(
        id="step-2",
        number=2,
        title="Verificar protocolos de ruteo",
        description=(
            'Efectuar en cualquiera de los routers el comando "show ip protocols". '
            "Dicho comando no mostrará nada por el hecho de que en el equipo no se encuentra "
            "configurado ningún protocolo de ruteo."
        ),
        checks=[
            ExerciseCheck(
                devices=ROUTERS,
                command=r"^show\s+ip\s+protocols$",
                description="Run show ip protocols on any router",
            )
        ],
    ),
    Exercise(
        id="step-3",
        number=3,
        title="Configurar direcciones IP en todos los routers",
        description=(
            "Configurar en todos los routers las direcciones IP indicadas. "
            "Ejemplo para eth1 del router R1:\n"
            "R1#conf t\nR1(config)#interface eth1\n"
            "R1(config-if)#ip address 10.10.10.1/24\n"
            "R1(config-if)#no shutdown"
        ),
        checks=[
            ExerciseCheck(
                devices=["r1"],
                command=r"ip\s+address\s+10\.10\.10\.1(?:/24|\s+255\.255\.255\.0)",
                description="R1 LAN IP",
            ),
            ExerciseCheck(
                devices=["r1"],
                command=r"ip\s+address\s+10\.1\.2\.1(?:/24|\s+255\.255\.255\.0)",
                description="R1 link to R2",
            ),
            ExerciseCheck(
                devices=["r2"],
                command=r"ip\s+address\s+10\.20\.20\.1(?:/24|\s+255\.255\.255\.0)",
                description="R2 LAN IP",
            ),
            ExerciseCheck(
                devices=["r2"],
                command=r"ip\s+address\s+10\.1\.2\.2(?:/24|\s+255\.255\.255\.0)",
                description="R2 link to R1",
            ),
            ExerciseCheck(
                devices=["r2"],
                command=r"ip\s+address\s+10\.2\.3\.(?:1|2)(?:/24|\s+255\.255\.255\.0)",
                description="R2 link to R3",
            ),
            ExerciseCheck(
                devices=["r3"],
                command=r"ip\s+address\s+10\.30\.30\.1(?:/24|\s+255\.255\.255\.0)",
                description="R3 LAN IP",
            ),
            ExerciseCheck(
                devices=["r3"],
                command=r"ip\s+address\s+10\.2\.3\.(?:2|3)(?:/24|\s+255\.255\.255\.0)",
                description="R3 link to R2",
            ),
        ],
    ),
    Exercise(
        id="step-4",
        number=4,
        title="Verificar interfaces con show ip interface brief",
        description=(
            'Verificar el estado de la configuración aplicada con el comando '
            '"show ip interface brief" o "show interface brief". Las interfaces '
            'configuradas tendrían que estar up.'
        ),
        checks=[
            ExerciseCheck(
                devices=ROUTERS,
                command=r"^show\s+(?:ip\s+)?interface\s+brief$",
                output_includes=["10."],
                description="Show interface brief with configured IPs",
            )
        ],
    ),
    Exercise(
        id="step-5",
        number=5,
        title="Ping al vecino inmediato",
        description=(
            "Verificar que se puede llegar al equipo vecino inmediato mediante el comando ping. "
            "Ejemplo desde R1 a R2: ping 10.1.2.2"
        ),
        checks=[
            ExerciseCheck(
                devices=["r1"],
                command=r"^ping\s+10\.1\.2\.2\b",
                output_includes=["64 bytes", "10.1.2.2"],
                description="R1 pings R2",
            )
        ],
    ),
    Exercise(
        id="step-6",
        number=6,
        title="Verificar rutas conectadas (C)",
        description=(
            'Efectuar en cualquiera de los routers el comando "show ip route". '
            "Notar que en este caso sí se observan algunas entradas en la tabla de ruteo. "
            "Las mismas poseen al comienzo de cada línea la letra C, que hace referencia "
            "a una red directamente conectada."
        ),
        checks=[
            ExerciseCheck(
                devices=ROUTERS,
                command=r"^show\s+ip\s+route$",
                output_includes=["C>*", "10."],
                description="show ip route shows connected (C) routes",
            )
        ],
    ),
    Exercise(
        id="step-7",
        number=7,
        title="Rutas estáticas en R1",
        description=(
            "Configurar en R1 las rutas estáticas para llegar a las redes 10.20.20.0/24 "
            "y 10.30.30.0/24.\nEjemplo: ip route 10.20.20.0/24 10.1.2.2"
        ),
        checks=[
            ExerciseCheck(
                devices=["r1"],
                command=r"ip\s+route\s+10\.20\.20\.0(?:/24|\s+255\.255\.255\.0)\s+10\.1\.2\.2",
            ),
            ExerciseCheck(
                devices=["r1"],
                command=r"ip\s+route\s+10\.30\.30\.0(?:/24|\s+255\.255\.255\.0)\s+10\.1\.2\.2",
            ),
        ],
    ),
    Exercise(
        id="step-8",
        number=8,
        title="Rutas estáticas en R2",
        description=(
            "Configurar en R2 las rutas estáticas para llegar a las redes 10.10.10.0/24 "
            "y 10.30.30.0/24."
        ),
        checks=[
            ExerciseCheck(
                devices=["r2"],
                command=r"ip\s+route\s+10\.10\.10\.0(?:/24|\s+255\.255\.255\.0)\s+10\.1\.2\.1",
            ),
            ExerciseCheck(
                devices=["r2"],
                command=r"ip\s+route\s+10\.30\.30\.0(?:/24|\s+255\.255\.255\.0)\s+10\.2\.3\.(?:2|3)",
            ),
        ],
    ),
    Exercise(
        id="step-9",
        number=9,
        title="Rutas estáticas en R3",
        description=(
            "Configurar en R3 las rutas estáticas para llegar a las redes 10.10.10.0/24 "
            "y 10.20.20.0/24."
        ),
        checks=[
            ExerciseCheck(
                devices=["r3"],
                command=r"ip\s+route\s+10\.10\.10\.0(?:/24|\s+255\.255\.255\.0)\s+10\.2\.3\.(?:1|2)",
            ),
            ExerciseCheck(
                devices=["r3"],
                command=r"ip\s+route\s+10\.20\.20\.0(?:/24|\s+255\.255\.255\.0)\s+10\.2\.3\.(?:1|2)",
            ),
        ],
    ),
    Exercise(
        id="step-10",
        number=10,
        title="Verificar rutas estáticas (S)",
        description=(
            'Verificar en los routers las redes configuradas con el comando "show ip route". '
            'Notar que las rutas configuradas en forma estática están indicadas por la letra "S".'
        ),
        checks=[
            ExerciseCheck(
                devices=ROUTERS,
                command=r"^show\s+ip\s+route$",
                output_includes=["S>*", "10."],
                description="show ip route shows static (S) routes",
            )
        ],
    ),
    Exercise(
        id="step-11",
        number=11,
        title="Ping desde PC_A a la LAN de R3",
        description=(
            "Desde la PC_A efectuar un ping a la dirección IP 10.30.30.10 de la LAN del router R3."
        ),
        checks=[
            ExerciseCheck(
                devices=["pc1"],
                command=r"^ping\s+(?:-c\s+\d+\s+)?10\.30\.30\.10\b",
                output_includes=["bytes from"],
                description="PC_A pings 10.30.30.10",
            )
        ],
    ),
]

LABS: dict[str, LabDefinition] = {
    "static-routing-lab-01": LabDefinition(
        id="static-routing-lab-01",
        title="Lab 01 — Ruteo Estático",
        description=(
            "Configura 3 routers y verifica conectividad con rutas estáticas. "
            "Topología bloqueada con consola IOS por dispositivo."
        ),
        category="routing",
        difficulty="medium",
        duration_minutes=90,
        tags=["static-routing", "ios", "ipv4"],
        enabled=True,
        exercise_count=len(STATIC_ROUTING_EXERCISES),
        path=STATIC_ROUTING_PATH,
        exercises=STATIC_ROUTING_EXERCISES,
        formula=LabFormula(
            provider="clab",
            protocol="ssh",
            port=5412,
            credentials=LabCredentials(username="root", password="clab123"),
            timeout_minutes=30,
            clab=ClabConfig(
                lab_name="rutas-estaticas",
                topology_file="rutas_estaticas.clab.yml",
                path=STATIC_ROUTING_PATH,
                entry_node="r1",
                node_credentials=LabCredentials(username="root", password="clab123"),
            ),
        ),
    ),
}
