from fastapi import FastAPI
from dotenv import load_dotenv

app = FastAPI()

def main():
    load_dotenv()  # Load environment variables from .env file
    import uvicorn 
    uvicorn.run(app, host="localhost", port=8000)
    
if __name__ == "__main__":    
    main()