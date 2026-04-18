import requests
import sys

ENDPOINT = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
TARGET_CATEGORY = "Principales Variables"
TIMEOUT = 10


def fetch_variables() -> list[dict]:
    try:
        response = requests.get(ENDPOINT, timeout=TIMEOUT, verify=True)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        print(f"Error: la request superó el timeout de {TIMEOUT}s.", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP {response.status_code}: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    return data.get("results", [])


def print_variables(variables: list[dict]) -> None:
    filtered = [v for v in variables if v.get("categoria") == TARGET_CATEGORY]

    if not filtered:
        print(f"No se encontraron variables en la categoría '{TARGET_CATEGORY}'.")
        return

    print(f"\n{'='*60}")
    print(f"Categoría: {TARGET_CATEGORY}  ({len(filtered)} variables)")
    print(f"{'='*60}")
    print(f"{'idVariable':<14} {'Periodicidad':<14} Descripción")
    print(f"{'-'*60}")
    for v in filtered:
        id_var = v.get("idVariable", "")
        descripcion = v.get("descripcion", "")
        periodicidad = v.get("periodicidad", "")
        print(f"{id_var:<14} {periodicidad:<14} {descripcion}")


if __name__ == "__main__":
    variables = fetch_variables()
    print_variables(variables)
