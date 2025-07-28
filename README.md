# MyDFI Backend

This is the backend API for MyDFI.  
It provides endpoints to:
- Autocomplete drug names
- Fetch existing user medications
- Add and delete medications



## Tech Stack
- Framework: FastAPI (Python 3)
- Database: MongoDB Atlas
- Deployment: Render



## Local Development Setup

1. Clone repository
   git clone https://github.com/<moneiraa>/myDFI-backend.git
   cd myDFI-backend

2. Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate   (Mac/Linux)
   venv\Scripts\activate      (Windows)

3. Install dependencies
   pip install -r requirements.txt

4. Add environment variable  
   Create a `.env` file in the project root with:  
   MONGODB_URI=<your MongoDB connection string>

5. Run backend
   uvicorn main:app --reload --port 8000
   Access API at http://127.0.0.1:8000



## Deployment
Backend is deployed on Render:  
https://mydfi.onrender.com



## API Endpoints
- GET /autocomplete?q=<query> → drug dropdown list suggestions
- GET /autofill?input_name=<name> → match drug details
- GET /get_medications?user_id=1 → fetch user medications
- POST /add_medication → add medication
- DELETE /delete_medication → delete medication
