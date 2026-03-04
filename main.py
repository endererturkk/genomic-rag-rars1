import json
from rag.pipeline import run_query

def main():
    query = input("Enter your query: ")

    result = run_query(query)

    print("\n--- VALIDATED OUTPUT ---\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()