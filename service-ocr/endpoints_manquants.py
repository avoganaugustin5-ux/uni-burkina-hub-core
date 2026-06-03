# Copiez ces 2 fonctions dans service-ocr/main.py
# Juste avant la ligne :  # ── 8. SCAN SIMPLE + GED



# ── /ocr/retranscrire  (appelé par ocr_studio.html) ───────────────────────────
@app.post("/ocr/retranscrire",
          summary="Retranscrire N images via OCR — alias scan-multi pour ocr_studio")
async def retranscrire(
    files:         List[UploadFile] = File(...),
    langue:        str              = Form("fra"),
    ordre:         str              = Form(""),
    authorization: Optional[str]   = Header(None),
    db:            Session          = Depends(get_db)
):
    user       = await verifier_token(authorization)
    session_id = uuid.uuid4().hex[:12]
    chemins    = []

    for f in files:
        if f.content_type not in IMAGE_MIMES:
            raise HTTPException(400, f"{f.filename} : format non supporte")
        chemin = sauvegarder_image(f, files.index(f) if hasattr(files,'index') else 0, session_id)
        chemins.append(chemin)

    if ordre.strip():
        try:
            indices = [int(x) for x in ordre.split(",")]
            if len(indices) == len(chemins):
                chemins = [chemins[i] for i in indices]
        except Exception:
            pass

    texte_global = ""
    resultats    = []
    for i, chemin in enumerate(chemins):
        t = ocr_image(chemin, langue)
        resultats.append({"index": i, "nom_fichier": chemin.name,
                          "texte_extrait": t, "nb_mots": len(t.split())})
        texte_global += t + "\n\n"

    texte_global = texte_global.strip()

    doc = DocumentOCR(
        nom_fichier_orig = files[0].filename if files else "scan",
        chemin_source    = str([str(c) for c in chemins]),
        texte_extrait    = texte_global,
        nb_pages         = len(files),
        nb_images        = len(files),
        statut           = "RETRANSCRIT",
        langue           = langue,
        date_traitement  = datetime.now(),
        id_utilisateur   = user.get("id_utilisateur") if user else None,
        role_soumetteur  = user.get("role") if user else None,
    )
    db.add(doc); db.commit(); db.refresh(doc)

    return {
        "id_ocr":             doc.id_ocr,
        "nb_images":          len(files),
        "nb_mots":            len(texte_global.split()),
        "langue":             langue,
        "statut":             "RETRANSCRIT",
        "resultats_par_image": resultats,
        "texte_consolide":    texte_global,
        "texte_extrait":      texte_global,
        "message":            f"{len(files)} image(s) retranscrite(s) avec succes."
    }


# ── /ocr/generer-document  (appelé par ocr_studio.html) ──────────────────────
@app.post("/ocr/generer-document",
          summary="Générer document final et retourner le fichier directement (blob)")
async def generer_document_direct(
    files:         List[UploadFile] = File(...),
    titre:         str              = Form("Document OCR"),
    format_sortie: str              = Form("pdf"),
    texte_corrige: str              = Form(""),
    mode_images:   str              = Form("false"),
    langue:        str              = Form("fra"),
    authorization: Optional[str]   = Header(None),
    db:            Session          = Depends(get_db)
):
    fmt = format_sortie.lower().strip()
    if fmt not in FORMATS_SUPPORTES:
        raise HTTPException(400, f"Format '{fmt}' non supporte. Choisissez : {FORMATS_SUPPORTES}")

    user       = await verifier_token(authorization)
    session_id = uuid.uuid4().hex[:12]
    chemins    = []

    for i, f in enumerate(files):
        if f.content_type not in IMAGE_MIMES:
            raise HTTPException(400, f"{f.filename} : format image non supporte")
        chemin = sauvegarder_image(f, i, session_id)
        chemins.append(chemin)

    use_images = (mode_images.lower() == "true")
    if use_images and fmt != "pdf":
        raise HTTPException(400, "Mode images directes uniquement disponible en PDF")

    if texte_corrige.strip():
        texte = texte_corrige.strip()
    elif not use_images:
        texte = "\n\n".join(ocr_image(c, langue) for c in chemins).strip()
    else:
        texte = ""

    try:
        chemin_dest = dispatcher_generation(fmt, texte, titre,
                                            images=chemins if use_images else None,
                                            mode_images=use_images)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Erreur generation : {e}")

    taille = chemin_dest.stat().st_size if chemin_dest.exists() else 0

    doc = DocumentOCR(
        nom_fichier_orig = files[0].filename if files else "document",
        chemin_source    = str([str(c) for c in chemins]),
        chemin_pdf       = str(chemin_dest),
        texte_extrait    = texte,
        texte_corrige    = texte_corrige.strip() or None,
        nb_pages         = len(files),
        nb_images        = len(files),
        format_sortie    = fmt,
        taille_fichier   = taille,
        statut           = "GENERE",
        langue           = langue,
        date_traitement  = datetime.now(),
        id_utilisateur   = user.get("id_utilisateur") if user else None,
        role_soumetteur  = user.get("role") if user else None,
    )
    db.add(doc); db.commit(); db.refresh(doc)

    mime_map = {
        "pdf":  "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "txt":  "text/plain; charset=utf-8",
        "md":   "text/markdown; charset=utf-8",
    }
    mime     = mime_map.get(fmt, "application/octet-stream")
    filename = (titre.replace(" ","_")[:40] or "document") + "." + fmt

    if not chemin_dest.exists():
        raise HTTPException(500, "Fichier genere introuvable")

    return FileResponse(
        path=str(chemin_dest), media_type=mime, filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

