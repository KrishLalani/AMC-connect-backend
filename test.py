import json
from model import detect_municipal_issue

def main():
    # Example image URL — replace with a real one
    image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTUDBQLOLyIq5F6n5LphtGNrCo-0yjfn6aUJg&s"

    print("Analyzing image from URL...")
    result = detect_municipal_issue(image_url)

    if isinstance(result, dict):
        print("Result:\n")
        print(json.dumps(result, indent=2))
    else:
        print("Message:", result)

if __name__ == "__main__":
    main()
