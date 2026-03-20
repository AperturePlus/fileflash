from fastapi import FastAPI
from dotenv import load_dotenv

app = FastAPI()

def main():
    load_dotenv()  # Load environment variables from .env file
    import uvicorn 
    uvicorn.run(app, host="localhost", port=8000)
    
@app.get("/hello")
def greeting():
    return {
        "message": "Hello, World!"
    }
    
if __name__ == "__main__":    
    main()