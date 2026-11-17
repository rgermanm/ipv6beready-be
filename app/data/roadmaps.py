from app.models.roadmap import (
    RoadmapDefinition,
    RoadmapEdge,
    RoadmapModule,
    RoadmapNode,
    RoadmapPosition,
)

IPV6_FOUNDATIONS = RoadmapDefinition(
    id="ipv6-foundations",
    slug="ipv6-foundations",
    title="IPv6 Foundations",
    description=(
        "Construye la base: por qué existe IPv6, cómo se estructuran las "
        "direcciones y cómo un host obtiene conectividad automáticamente."
    ),
    difficulty="easy",
    estimated_hours=6,
    tags=["ipv6", "addressing", "slaac"],
    stage="Fundamentos IPv6",
    stage_order=1,
    stage_summary="Adquiere las bases de direccionamiento IPv6 para empezar a operar redes dual-stack.",
    highlights=[
        "Entiende el espacio de direcciones IPv6",
        "Lee y planifica prefijos /64 y /48",
        "Domina SLAAC, DHCPv6 e ICMPv6",
    ],
    modules=[
        RoadmapModule(
            id="concepts",
            title="Conceptos",
            summary="Por qué IPv6 y cómo se ve una dirección.",
            node_ids=["why-ipv6", "addressing"],
        ),
        RoadmapModule(
            id="autoconfig",
            title="Autoconfiguración",
            summary="Cómo un host obtiene dirección y conectividad.",
            node_ids=["slaac", "icmpv6"],
        ),
    ],
    nodes=[
        RoadmapNode(
            id="why-ipv6",
            kind="skill",
            title="Por qué IPv6",
            description="Agotamiento de IPv4, dual-stack y el modelo extremo a extremo.",
            module_id="concepts",
            icon="network",
            position=RoadmapPosition(x=40, y=80),
        ),
        RoadmapNode(
            id="addressing",
            kind="skill",
            title="Addressing",
            description="Unicast, multicast, link-local, GUA y planificación de prefijos.",
            module_id="concepts",
            icon="binary",
            position=RoadmapPosition(x=40, y=260),
        ),
        RoadmapNode(
            id="slaac",
            kind="skill",
            title="SLAAC y DHCPv6",
            description="Autoconfiguración de direcciones, RA y opciones DHCPv6.",
            module_id="autoconfig",
            icon="workflow",
            position=RoadmapPosition(x=360, y=80),
        ),
        RoadmapNode(
            id="icmpv6",
            kind="skill",
            title="ICMPv6",
            description="Neighbor Discovery, Echo y los mensajes que reemplazan ARP.",
            module_id="autoconfig",
            icon="radio",
            position=RoadmapPosition(x=360, y=260),
        ),
    ],
    edges=[
        RoadmapEdge(id="e-why-addr", source="why-ipv6", target="addressing"),
        RoadmapEdge(id="e-addr-slaac", source="addressing", target="slaac"),
        RoadmapEdge(id="e-slaac-icmp", source="slaac", target="icmpv6"),
        RoadmapEdge(id="e-addr-icmp", source="addressing", target="icmpv6"),
    ],
)

IPV6_ROUTING = RoadmapDefinition(
    id="ipv6-routing",
    slug="ipv6-routing",
    title="IPv6 Routing",
    description=(
        "Enruta IPv6 en el laboratorio: estático primero, luego BGP, "
        "con topologías reales en containerlab."
    ),
    difficulty="medium",
    estimated_hours=10,
    tags=["routing", "bgp", "static"],
    stage="Routing y protocolos",
    stage_order=2,
    stage_summary="Aprende a mover tráfico IPv6 entre redes con labs prácticos.",
    highlights=[
        "Configura rutas estáticas extremo a extremo",
        "Levanta BGP entre routers FRR",
        "Verifica conectividad IPv4 e IPv6",
    ],
    modules=[
        RoadmapModule(
            id="static",
            title="Ruteo estático",
            summary="Primer laboratorio guiado con ejercicios.",
            node_ids=["static-routing"],
        ),
        RoadmapModule(
            id="dynamic",
            title="Ruteo dinámico",
            summary="BGP en una topología de tres routers y PCs.",
            node_ids=["lab-bgp"],
        ),
        RoadmapModule(
            id="policy",
            title="Política",
            summary="Siguiente paso: filtrado y política de ruteo IPv6.",
            node_ids=["routing-policy"],
        ),
    ],
    nodes=[
        RoadmapNode(
            id="static-routing",
            kind="lab",
            title="Ruteo estático",
            description="Tres routers y PCs. Configura rutas y verifica conectividad.",
            lab_slug="static-routing-lab-01",
            module_id="static",
            icon="route",
            difficulty="medium",
            position=RoadmapPosition(x=40, y=140),
        ),
        RoadmapNode(
            id="lab-bgp",
            kind="lab",
            title="BGP",
            description="Topología BGP con FRR y hosts Linux para anunciar prefijos.",
            lab_slug="lab-bgp",
            module_id="dynamic",
            icon="share-2",
            difficulty="medium",
            position=RoadmapPosition(x=360, y=140),
        ),
        RoadmapNode(
            id="routing-policy",
            kind="skill",
            title="Política de ruteo",
            description="Prefix-lists, route-maps y filtrado de anuncios IPv6.",
            module_id="policy",
            icon="filter",
            position=RoadmapPosition(x=680, y=140),
        ),
    ],
    edges=[
        RoadmapEdge(id="e-static-bgp", source="static-routing", target="lab-bgp"),
        RoadmapEdge(id="e-bgp-policy", source="lab-bgp", target="routing-policy"),
    ],
)

IPV6_SECURITY = RoadmapDefinition(
    id="ipv6-security",
    slug="ipv6-security",
    title="IPv6 Security",
    description=(
        "Defiende el plano IPv6: NDP, RA Guard, ACLs y el modelo de "
        "exposición de servicios en una red dual-stack."
    ),
    difficulty="hard",
    estimated_hours=8,
    tags=["security", "ndp", "firewall"],
    stage="Seguridad y operación",
    stage_order=3,
    stage_summary="Cierra el curso endureciendo IPv6 en el borde y en el acceso.",
    highlights=[
        "Controla Neighbor Discovery",
        "Aplica RA Guard y ACLs",
        "Piensa el ataque y la defensa sobre IPv6",
    ],
    modules=[
        RoadmapModule(
            id="ndp",
            title="Plano de vecindad",
            summary="NDP es el nuevo ARP: hay que vigilarlo.",
            node_ids=["ndp", "ra-guard"],
        ),
        RoadmapModule(
            id="hardening",
            title="Hardening",
            summary="Filtrado y cifrado sobre IPv6.",
            node_ids=["acls", "ipsec"],
        ),
    ],
    nodes=[
        RoadmapNode(
            id="ndp",
            kind="skill",
            title="NDP",
            description="Neighbor Solicitation/Advertisement y ataques de spoofing.",
            module_id="ndp",
            icon="radar",
            position=RoadmapPosition(x=40, y=140),
        ),
        RoadmapNode(
            id="ra-guard",
            kind="skill",
            title="RA Guard",
            description="Cómo un rogue RA hijackea el default gateway.",
            module_id="ndp",
            icon="shield",
            position=RoadmapPosition(x=320, y=140),
        ),
        RoadmapNode(
            id="acls",
            kind="skill",
            title="IPv6 ACLs",
            description="Filtrado de ICMPv6, extension headers y tráfico de datos.",
            module_id="hardening",
            icon="shield-check",
            position=RoadmapPosition(x=600, y=80),
        ),
        RoadmapNode(
            id="ipsec",
            kind="skill",
            title="IPsec",
            description="IPsec nativo en IPv6 para proteger el tránsito.",
            module_id="hardening",
            icon="lock",
            position=RoadmapPosition(x=600, y=260),
        ),
    ],
    edges=[
        RoadmapEdge(id="e-ndp-ra", source="ndp", target="ra-guard"),
        RoadmapEdge(id="e-ra-acls", source="ra-guard", target="acls"),
        RoadmapEdge(id="e-ra-ipsec", source="ra-guard", target="ipsec"),
    ],
)

ROADMAPS: dict[str, RoadmapDefinition] = {
    path.slug: path
    for path in (IPV6_FOUNDATIONS, IPV6_ROUTING, IPV6_SECURITY)
}
