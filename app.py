from flask import Flask, render_template, request
from algosdk import mnemonic, account
from algosdk.v2client import algod
from algosdk.transaction import AssetConfigTxn
from algosdk import transaction
from dotenv import load_dotenv
import os
import json

app = Flask(__name__)

# Load environment variables
load_dotenv()
MNEMONIC = os.getenv("MNEMONIC")

# Connect to Algorand Testnet
algod_address = "https://testnet-api.algonode.cloud"
algod_client = algod.AlgodClient("", algod_address)

# Convert mnemonic to private key
private_key = mnemonic.to_private_key(MNEMONIC)
sender_address = account.address_from_private_key(private_key)

# Create credentials file if not exists
if not os.path.exists("credentials.json"):
    with open("credentials.json", "w") as f:
        json.dump([], f)


# -------- NFT MINT FUNCTION --------
def mint_nft(student, degree, year):
    params = algod_client.suggested_params()

    txn = AssetConfigTxn(
        sender=sender_address,
        sp=params,
        total=1,
        decimals=0,
        default_frozen=False,
        unit_name="CERT",
        asset_name=f"{student}-{degree}-{year}",
        manager=sender_address,
        reserve=sender_address,
        freeze=sender_address,
        clawback=sender_address,
    )

    signed_txn = txn.sign(private_key)
    txid = algod_client.send_transaction(signed_txn)
    confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
    asset_id = confirmed_txn["asset-index"]

    return asset_id


# -------- ROUTES --------

@app.route("/")
def home():
    return render_template("institution.html")


@app.route("/issue", methods=["POST"])
def issue():
    student = request.form["student"]
    degree = request.form["degree"]
    year = request.form["year"]

    if not student or not degree or not year:
        return render_template("institution.html", message="All fields required!")

    try:
        asset_id = mint_nft(student, degree, year)

        # Save to JSON
        with open("credentials.json", "r") as f:
            data = json.load(f)

        data.append({
            "student": student,
            "degree": degree,
            "year": year,
            "asset_id": asset_id
        })

        with open("credentials.json", "w") as f:
            json.dump(data, f, indent=4)

        return render_template("institution.html",
                               message=f"Credential Issued! Asset ID: {asset_id}")

    except Exception as e:
        return render_template("institution.html",
                               message=f"Error: {str(e)}")


@app.route("/student", methods=["GET", "POST"])
def student():
    credentials = []

    if request.method == "POST":
        name = request.form["student"]

        with open("credentials.json", "r") as f:
            data = json.load(f)

        credentials = [c for c in data if c["student"] == name]

    return render_template("student.html", credentials=credentials)


@app.route("/verify", methods=["GET", "POST"])
def verify():
    message = None

    if request.method == "POST":
        asset_id = request.form["asset_id"]

        try:
            algod_client.asset_info(int(asset_id))
            message = "Verified on Algorand Testnet ✅"
        except:
            message = "Invalid Credential ❌"

    return render_template("verify.html", message=message)


if __name__ == "__main__":
    app.run(debug=True)