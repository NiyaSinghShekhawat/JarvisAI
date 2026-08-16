from backend.brain.router import process_request
from backend.brain.router import get_router_status


def main():

    print("=" * 50)
    print("                 JARVIS")
    print("=" * 50)

    provider_info = get_router_status()

    provider = provider_info["provider"]
    model = provider_info["model"]

    print(
        f"Connected to {model} through {provider}."
    )

    print("Type 'exit' to shut down.\n")

    conversation = []

    while True:

        user_input = input("You: ").strip()

        if user_input.lower() == "exit":

            print("Jarvis: Shutting down.")
            break

        if not user_input:
            continue

        try:

            result = process_request(
                user_input,
                conversation
            )

            if result["type"] == "text":

                print(
                    f"\nJarvis: {result['content']}\n"
                )

            else:

                print(
                    f"\nJarvis: {result}\n"
                )

        except Exception as e:

            print(
                f"\n[ERROR] {e}\n"
            )


if __name__ == "__main__":
    main()