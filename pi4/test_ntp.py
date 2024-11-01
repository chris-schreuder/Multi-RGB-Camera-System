import requests

def get_online_time():
    try:
        response = requests.get('http://worldtimeapi.org/api/ip')
        response.raise_for_status()  # Check for errors in the HTTP response

        data = response.json()
        utc_time = data['utc_datetime']
        print(f"Universal Time (UTC): {utc_time}")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_online_time()
