"""Supply Python functions to Nevso; all readings here are local mock data."""
import argparse
import json
from pathlib import Path
import sys

# Also runnable directly before an editable install, from this source checkout.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nevso import Agent, Tool, format_trace


def read_soil_ph(bed_id):
    return {"soil_ph": 6.4} if bed_id == "B-73" else {"error": "not_found"}


def read_soil_moisture(bed_id):
    return {"soil_moisture_percent": 38} if bed_id == "B-73" else {"error": "not_found"}


def read_water_tank_level(tank_id):
    return {"water_remaining_percent": 81} if tank_id == "W-26" else {"error": "not_found"}


def id_schema(name):
    return {"type": "object", "properties": {name: {"type": "string"}},
            "required": [name], "additionalProperties": False}


def tools():
    return [
        Tool("read_soil_moisture", {
            "en": "Read the soil moisture percentage in a planting bed.",
            "it": "Leggi la percentuale di umidità del terreno in un’aiuola.",
        }, id_schema("bed_id"), read_soil_moisture),
        Tool("read_soil_ph", {
            "en": "Read the soil pH measurement for a planting bed.",
            "it": "Leggi il valore del pH del terreno in un’aiuola.",
        }, id_schema("bed_id"), read_soil_ph),
        Tool("read_water_tank_level", {
            "en": "Read the percentage of water remaining in a storage tank.",
            "it": "Leggi la percentuale di acqua rimasta in un serbatoio.",
        }, id_schema("tank_id"), read_water_tank_level),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["gguf", "cuda"], default="gguf")
    parser.add_argument("--strategy", choices=["rank", "select", "none"], default="rank")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error("Use a fresh output path")
    rows = []
    with Agent(tools(), engine=args.engine, strategy=args.strategy) as agent:
        for lang, request in [
            ("it", "Leggi il pH del terreno nell’aiuola B-73."),
            ("en", "What percentage of water remains in tank W-26?"),
        ]:
            result = agent.run(request, language=lang)
            rows.append(result)
            print(format_trace(result), "\n")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as f:
            json.dump({"scope": "Three Python mock tools, two example requests; not a benchmark.",
                       "rows": rows}, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Saved:", args.output)


if __name__ == "__main__":
    main()
