from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.constants import ALLOWED_EVIDENCE_TYPES, MAX_EVIDENCE_FILE_SIZE_BYTES
from app.supabase_client import EVIDENCE_BUCKET, supabase

router = APIRouter(prefix="/evidence", tags=["Evidence"])


def _get_transaction(transaction_id: str):
    return (
        supabase.table("transactions")
        .select("transaction_id")
        .eq("transaction_id", transaction_id)
        .execute()
        .data
    )


def _get_refund(refund_id: int):
    return (
        supabase.table("refunds")
        .select("id, transaction_id")
        .eq("id", refund_id)
        .execute()
        .data
    )


@router.post("/upload", status_code=201)
async def upload_evidence(
    transaction_id: str = Form(...),
    refund_id: int | None = Form(None),
    file: UploadFile = File(...),
):
    transaction_id = transaction_id.strip()
    if not transaction_id:
        raise HTTPException(status_code=400, detail="Transaction ID is required")

    if not _get_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")

    if refund_id is not None:
        refund = _get_refund(refund_id)
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found")
        if refund[0]["transaction_id"] != transaction_id:
            raise HTTPException(status_code=400, detail="This refund does not belong to the selected transaction")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a file to upload")

    if file.content_type not in ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG and PDF files are allowed")

    file_data = await file.read()

    if not file_data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")

    if len(file_data) > MAX_EVIDENCE_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File is too large (10 MB limit)")

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    file_path = f"{transaction_id}/{safe_name}"

    try:
        supabase.storage.from_(EVIDENCE_BUCKET).upload(
            file_path,
            file_data,
            {"content-type": file.content_type, "upsert": "true"},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not upload file to storage: {exc}") from exc

    evidence_row = {
        "transaction_id": transaction_id,
        "file_name": file.filename,
        "file_path": file_path,
        "file_type": file.content_type,
    }
    if refund_id is not None:
        evidence_row["refund_id"] = refund_id

    response = supabase.table("evidence").insert(evidence_row).execute()

    return {
        "message": "Evidence uploaded successfully",
        "evidence": response.data[0] if response.data else evidence_row,
    }


@router.get("/")
def list_all_evidence():
    response = supabase.table("evidence").select("*").order("uploaded_at", desc=True).execute()
    return response.data


@router.get("/{transaction_id}")
def get_transaction_evidence(transaction_id: str):
    if not _get_transaction(transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")

    response = (
        supabase.table("evidence")
        .select("*")
        .eq("transaction_id", transaction_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return response.data


@router.get("/{evidence_id}/link")
def get_evidence_link(evidence_id: int):
    rows = supabase.table("evidence").select("*").eq("id", evidence_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Evidence not found")

    file_path = rows[0]["file_path"]

    try:
        signed = supabase.storage.from_(EVIDENCE_BUCKET).create_signed_url(file_path, 300)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Could not generate a link for this file: {exc}") from exc

    url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("signed_url")
    if not url:
        raise HTTPException(status_code=500, detail="Could not generate a link for this file")

    return {"url": url}


@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: int):
    existing = supabase.table("evidence").select("*").eq("id", evidence_id).execute().data
    if not existing:
        raise HTTPException(status_code=404, detail="Evidence not found")

    try:
        supabase.storage.from_(EVIDENCE_BUCKET).remove([existing[0]["file_path"]])
    except Exception:  # noqa: BLE001
        pass  # if the file is already gone from storage, still remove the DB row

    supabase.table("evidence").delete().eq("id", evidence_id).execute()

    return {"message": "Evidence deleted successfully", "evidence_id": evidence_id}
