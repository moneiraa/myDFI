from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

app = FastAPI()

# ======== ENABLE CORS ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======== CONNECT TO MONGODB ========
uri = "mongodb+srv://moneira:4tqxYrl0sLpm6L0F@dfisaudi.e7wbnvh.mongodb.net/?retryWrites=true&w=majority&appName=DFISaudi"
try:
    client = MongoClient(uri)
    sfda_collection = client['SFDA']['SFDA_drugs']
    user_collection = client['DFIchecker']['user_medication_list']
    interactions_collection = client['DFIchecker']['drug_food_interactions']
    client.admin.command('ping')
    print("Connected to MongoDB successfully")
except Exception as e:
    print("MongoDB connection error:", e)

# ======== AUTOCOMPLETE ============
@app.get("/autocomplete")
def autocomplete(q: str = Query(...)):
    try:
        print(f"DEBUG: Autocomplete query received: {q}")
        regex = {"$regex": q, "$options": "i"}
        docs = list(sfda_collection.find(
            {"$or": [{"trade_name": regex}, {"scientific_name": regex}]},
            {"_id": 0, "sfda_drug_id": 1, "trade_name": 1, "scientific_name": 1}
        ).limit(15))
        print(f"DEBUG: Found {len(docs)} matches")
        results = []
        for doc in docs:
            if q.lower() in (doc.get("trade_name", "").lower()):
                results.append({
                    "type": "trade_name",
                    "trade_name": doc.get("trade_name", ""),
                    "scientific_name": doc.get("scientific_name", ""),
                    "sfda_drug_id": doc.get("sfda_drug_id", "")
                })
            if q.lower() in (doc.get("scientific_name", "").lower()):
                results.append({
                    "type": "scientific_name",
                    "scientific_name": doc.get("scientific_name", ""),
                    "trade_name": doc.get("trade_name", ""),
                    "sfda_drug_id": doc.get("sfda_drug_id", "")
                })
        return {"results": results}
    except Exception as e:
        print("Autocomplete error:", e)
        return {"error": str(e)}

# ======== AUTOFILL ============
@app.get("/autofill")
def autofill(input_name: str):
    try:
        print(f"DEBUG: Autofill query: {input_name}")
        drug = sfda_collection.find_one(
            {"$or": [
                {"trade_name": {"$regex": f"^{input_name}$", "$options": "i"}},
                {"scientific_name": {"$regex": f"^{input_name}$", "$options": "i"}}
            ]},
            {"_id": 0, "sfda_drug_id": 1, "trade_name": 1, "scientific_name": 1}
        )
        return drug if drug else {"error": "Name not found in SFDA dataset."}
    except Exception as e:
        print("Autofill error:", e)
        return {"error": str(e)}

# ======== ADD MEDICATION ============
class Medication(BaseModel):
    sfda_drug_id: str
    trade_name: str
    scientific_name: str
    duration: str
    user_id: str = "1"

@app.post("/add_medication")
def add_medication(med: Medication):
    try:
        print(f"DEBUG: Add medication payload: {med.dict()}")
        parts = med.duration.split(" - ") if med.duration else []
        start_date = None
        end_date = None

        if len(parts) > 0 and parts[0].strip():
            start_date = datetime.strptime(parts[0].strip(), "%d/%m/%Y")
        if len(parts) > 1 and parts[1].strip() and parts[1].strip().lower() != "ongoing":
            end_date = datetime.strptime(parts[1].strip(), "%d/%m/%Y")

        if start_date is None:
            start_date = datetime.utcnow()
        if end_date is not None and start_date > end_date:
            return {"error": "Start date cannot be after end date."}

        doc = {
            "user_id": med.user_id,
            "sfda_drug_id": med.sfda_drug_id,
            "drug_trade_name": med.trade_name,
            "drug_scientific_name": med.scientific_name,
            "drug_duration_start_date": start_date,
            "drug_duration_end_date": end_date,
            "processed": 0  # required field default value
        }
        result = user_collection.insert_one(doc)
        print(f"DEBUG: Medication inserted with ID: {result.inserted_id}")
        return {"message": "Medication added to MongoDB successfully.", "inserted_id": str(result.inserted_id)}
    except Exception as e:
        print("Error inserting medication:", e)
        return {"error": str(e)}

# ======== GET MEDICATIONS ============
@app.get("/get_medications")
def get_medications(user_id: str = "1"):
    try:
        meds = list(user_collection.find({"user_id": user_id}))
        for med in meds:
            med["_id"] = str(med["_id"])
        return {"count": len(meds), "medications": meds}
    except Exception as e:
        print("Error fetching medications:", e)
        return {"error": str(e)}

# ======== DELETE MEDICATION (ALSO DELETE INTERACTIONS) ============
@app.delete("/delete_medication")
def delete_medication(data: dict = Body(...)):
    try:
        med_id = data.get("_id")
        if not med_id:
            return {"error": "Medication _id is required for deletion."}

        # Find medication info before deletion (for interaction query)
        med_doc = user_collection.find_one({"_id": ObjectId(med_id)})
        if not med_doc:
            return {"error": "No matching medication found."}

        # Delete medication
        med_result = user_collection.delete_one({"_id": ObjectId(med_id)})
        if med_result.deleted_count == 1:
            # Delete related interactions
            trade_name = med_doc.get("drug_trade_name")
            user_id = med_doc.get("user_id")
            inter_result = interactions_collection.delete_many({
                "trade_name": trade_name,
                "user_id": user_id
            })
            print(f"DEBUG: Deleted medication {med_id} and {inter_result.deleted_count} related interactions")
            return {"message": "Medication and related interactions deleted successfully."}

        print(f"DEBUG: No medication matched _id {med_id}")
        return {"message": "No matching medication found."}
    except Exception as e:
        print("Error deleting medication:", e)
        return {"error": str(e)}
