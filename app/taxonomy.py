from __future__ import annotations


TAXONOMY = [
    ("Ciberseguridad ofensiva", "offensive-security", None, "Pentesting, bug bounty y análisis de vulnerabilidades"),
    ("Bug Bounty", "bug-bounty", "offensive-security", "Programas, reportes y metodología de bug bounty"),
    ("Recon/OSINT", "recon-osint", "offensive-security", "Reconocimiento, enumeración y OSINT"),
    ("Web/API", "web-api", "offensive-security", "Seguridad de aplicaciones web y APIs"),
    ("XSS/CSP", "xss-csp", "offensive-security", "Cross-site scripting, DOM y Content Security Policy"),
    ("SSRF", "ssrf", "offensive-security", "Server-side request forgery"),
    ("SQLi", "sqli", "offensive-security", "Inyección SQL"),
    ("Auth/IDOR/OAuth", "auth-idor-oauth", "offensive-security", "Autenticación, autorización, IDOR y OAuth"),
    ("RCE/Uploads", "rce-uploads", "offensive-security", "Ejecución remota y subida de archivos"),
    ("GraphQL", "graphql", "offensive-security", "Seguridad y tooling GraphQL"),
    ("Cloud", "cloud-security", "offensive-security", "Seguridad en nubes públicas"),
    ("Mobile Android/iOS", "mobile-security", "offensive-security", "Seguridad móvil Android e iOS"),
    ("Vulnerability Research", "vulnerability-research", "offensive-security", "CVEs, reversing e investigación"),
    ("Seguridad de IA", "ai-security", "offensive-security", "Seguridad de LLMs y sistemas de IA"),
    ("IA y agentes", "ai-agents", None, "Inteligencia artificial, modelos y agentes"),
    ("LLMs", "llms", "ai-agents", "Large language models"),
    ("Coding Agents", "coding-agents", "ai-agents", "Agentes de programación"),
    ("Harnesses", "harnesses", "ai-agents", "Harnesses y evaluación de agentes"),
    ("MCP", "mcp", "ai-agents", "Model Context Protocol"),
    ("Prompts", "prompts", "ai-agents", "Prompting e instrucciones"),
    ("Automatización", "automation", "ai-agents", "Automatización asistida por IA"),
    ("Modelos", "models", "ai-agents", "Modelos y embeddings"),
    ("Desarrollo y sistemas", "development-systems", None, "Programación, sistemas y operaciones"),
    ("Programación", "programming", "development-systems", "Lenguajes, librerías y patrones"),
    ("Linux/macOS", "linux-macos", "development-systems", "Linux, macOS y terminal"),
    ("DevTools", "devtools", "development-systems", "Herramientas de desarrollo"),
    ("VPS", "vps", "development-systems", "Servidores VPS"),
    ("Self-hosting/HomeLab", "self-hosting", "development-systems", "Servicios propios y homelab"),
    ("Redes", "networks", "development-systems", "Redes y protocolos"),
    ("Finanzas y economía", "finance-economy", "other-interests", "Finanzas, inversión y economía"),
    ("Viajes", "travel", "other-interests", "Viajes, destinos y planificación"),
    ("Fotografía", "photography", "other-interests", "Fotografía, cámaras y edición"),
    ("Videojuegos", "videogames", None, "Videojuegos"),
    ("Pokémon/VGC", "pokemon-vgc", "videogames", "Pokémon competitivo y VGC"),
    ("Nintendo", "nintendo", "videogames", "Nintendo"),
    ("Retro y otros", "retro-games", "videogames", "Retro y otros videojuegos"),
    ("Aprendizaje y cultura", "learning-culture", "other-interests", "Historia, ciencia, idiomas y cultura"),
    ("Otros intereses", "other-interests", None, "Otros temas personales"),
    ("Fútbol/Celta", "football-celta", "other-interests", "Fútbol y Celta de Vigo"),
    ("Entretenimiento", "entertainment", "other-interests", "Cine, series y música"),
    ("Compras", "shopping", "other-interests", "Productos y compras"),
    ("Hogar", "home", "other-interests", "Hogar y vida diaria"),
]


CATEGORY_TERMS = {
 "bug-bounty": ["bug bounty","hackerone","bugcrowd","bounty report","responsible disclosure"],
 "recon-osint": ["recon","osint","subdomain","subfinder","amass","nuclei","linkfinder","jsluice","gau ","wayback","endpoint discovery"],
 "web-api": ["web security","api security","rest api","http request","web app","postmessage"],
 "xss-csp": ["xss","cross-site scripting","content security policy"," csp","dom clobbering","postmessage"],
 "ssrf": ["ssrf","server-side request forgery","dns rebinding"],
 "sqli": ["sqli","sql injection","injection sql"],
 "auth-idor-oauth": ["idor","oauth","authentication bypass","authorization bypass","account takeover","jwt","saml"],
 "rce-uploads": ["rce","remote code execution","file upload","command injection","webshell"],
 "graphql": ["graphql","introspection query"],
 "cloud-security": ["aws security","azure security","gcp security","s3 bucket","cloud security","iam privilege"],
 "mobile-security": ["android security","ios security","apk","frida","objection","mobile pentest"],
 "vulnerability-research": ["cve-","0day","zero-day","vulnerability research","reverse engineering","exploit"],
 "ai-security": ["prompt injection","llm security","ai security","jailbreak","model poisoning"],
 "llms": ["llm","large language model","transformer","embedding","rag ","gpt-","claude","gemini"],
 "coding-agents": ["coding agent","codex","claude code","cursor","copilot","agentic coding"],
 "harnesses": ["agent harness","eval harness","agent evaluation","benchmark agent"],
 "mcp": ["model context protocol","mcp server","mcp client"],
 "prompts": ["system prompt","prompt engineering","prompting"],
 "automation": ["automation","workflow","n8n","zapier","automate"],
 "models": ["onnx","hugging face","model release","fine-tun","quantization","weights"],
 "programming": ["python","javascript","typescript","rust","golang","github","source code","library","framework"],
 "linux-macos": ["linux","macos","shell","terminal","bash","zsh"],
 "devtools": ["devtool","debugger","visual studio code","vscode","git ","cli tool"],
 "vps": ["vps","virtual private server","digitalocean","hetzner"],
 "self-hosting": ["self-host","homelab","raspberry pi","docker compose","home server"],
 "networks": ["networking","tcp","udp","dns","wi-fi","vpn","tailscale"],
 "finance-economy": ["finance","stock market","investing","inflation","economy","bitcoin","ethereum","etf"],
 "travel": ["travel","flight","hotel","trip to","tourism","viaje","vuelo"],
 "photography": ["photography","camera","lens","lightroom","photoshop","fotografía","sony alpha","fujifilm"],
 "pokemon-vgc": ["pokémon","pokemon"," vgc","pokédex","pokedex"],
 "nintendo": ["nintendo","switch 2","zelda","mario"],
 "retro-games": ["retrogaming","retro game","playstation","xbox","steam","fortnite","video game"],
 "learning-culture": ["history","science","book recommendation","learning","course","museum","culture"],
 "football-celta": ["celta","fútbol","football","la liga","champions league"],
 "entertainment": ["movie","cinema","tv series","netflix","music","film","trailer"],
 "shopping": ["discount","deal","buy","amazon","price","oferta","comprar"],
 "home": ["home improvement","kitchen","recipe","garden","furniture","hogar"],
}


TAG_TERMS = {
 "SSRF":["ssrf","server-side request forgery"], "XSS":["xss","cross-site scripting"],
 "CSP":["content security policy"," csp"], "IDOR":["idor"], "OAuth":["oauth"],
 "Nuclei":["nuclei"], "Recon":["recon","subdomain"], "OSINT":["osint"],
 "JavaScript":["javascript","jsluice","linkfinder"], "Python":["python"],
 "MCP":["model context protocol","mcp server"], "LLM":["llm","large language model"],
 "Docker":["docker"], "Raspberry Pi":["raspberry pi"], "Pokémon":["pokemon","pokémon"],
 "CVE":["cve-"], "GraphQL":["graphql"], "Android":["android"], "iOS":["ios"],
}


def seed_taxonomy(connection) -> None:
    for order,(name,slug,parent,description) in enumerate(TAXONOMY):
        connection.execute("""
          INSERT INTO categories(name,slug,parent_id,description,sort_order) VALUES(?,?,?,?,?)
          ON CONFLICT(slug) DO UPDATE SET name=excluded.name,
           description=excluded.description,sort_order=excluded.sort_order
        """, (name,slug,None,description,order))
    ids = {row["slug"]:row["id"] for row in connection.execute(
        "SELECT id,slug FROM categories"
    )}
    for _,slug,parent,_ in TAXONOMY:
        connection.execute(
            "UPDATE categories SET parent_id=? WHERE slug=?",
            (ids.get(parent),slug),
        )
    connection.commit()
