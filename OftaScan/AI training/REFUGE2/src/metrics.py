import cv2
import numpy as np

def extract_clinical_parameters(pred_disc, pred_cup):
    # Vrši matematičku ekstrakciju kliničkih parametara iz binarnih maski UNet-a.
    # Izračunava CDR odnose (vCDR, hCDR, aCDR) i evaluira anatomsko ISNT pravilo.
    results = {
        "vCDR": 0.0,
        "hCDR": 0.0,
        "aCDR": 0.0,
        "rim_area_pixels": 0,
        "isnt_rule_valid": False,
        "quadrants_thickness": {"Inferior": 0, "Superior": 0, "Nasal": 0, "Temporal": 0},
        "diagnosis": "Healthy"
    }

    # Pretvaramo verovatnoće u binarne slike (0 i 255) za OpenCV konturne funkcije
    disc_img = (pred_disc * 255).astype(np.uint8)
    cup_img = (pred_cup * 255).astype(np.uint8)

    # Izdvajamo spoljne konture optičkog diska i ekskavacije (čašice)
    disc_contours, _ = cv2.findContours(disc_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cup_contours, _ = cv2.findContours(cup_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Ako model nije detektovao disk ili čašicu, vraćamo bazne (nulte) rezultate
    if len(disc_contours) == 0 or len(cup_contours) == 0:
        return results  

    # Uzimamo najveću konturu da bismo eliminisali eventualni šum i lažne pozitivne piksele
    c_disc = max(disc_contours, key=cv2.contourArea)
    c_cup = max(cup_contours, key=cv2.contourArea)

    # boundingRect daje spoljni pravougaonik (x, y, širina, visina) oko konture
    _, _, w_disc, h_disc = cv2.boundingRect(c_disc)
    _, _, w_cup, h_cup = cv2.boundingRect(c_cup)

    # Računanje vertikalnog (vCDR) i horizontalnog (hCDR) Cup-to-Disc odnosa
    vCDR = h_cup / max(1, h_disc)
    hCDR = w_cup / max(1, w_disc)

    # Površinski parametri (aCDR) i površina neuroretinalnog ruba (Rim Area) na osnovu broja piksela
    area_disc = np.sum(pred_disc)
    area_cup = np.sum(pred_cup)
    
    aCDR = area_cup / max(1, area_disc)
    rim_area = max(0, area_disc - area_cup)

    # Računamo centroid (geometrijski centar) optičkog diska preko slikovnih momenata
    M = cv2.moments(c_disc)
    if M["m00"] != 0:
        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
    else:
        cX, cY = disc_img.shape[1] // 2, disc_img.shape[0] // 2

    def get_rim_thickness(direction_x, direction_y):
        # Pomoćna funkcija koja ispaljuje 'zrak' iz centra diska u određenom smeru
        # i broji piksele koji pripadaju samo rubu (unutar diska, van šolje).
        thickness = 0
        curr_x, curr_y = cX, cY
        h, w = pred_disc.shape
        
        while 0 <= curr_x < w and 0 <= curr_y < h:
            in_disc = pred_disc[curr_y, curr_x] > 0
            in_cup = pred_cup[curr_y, curr_x] > 0
            
            # Ako smo u disku, a nismo ušli u čašicu, to je neuroretinalni rub
            if in_disc and not in_cup:
                thickness += 1
                
            # Izlazak izvan granica diska prekida brojanje debljine ruba
            if not in_disc and thickness > 0:
                break
                
            curr_x += direction_x
            curr_y += direction_y
        return thickness

    # Merenje debljine ruba u 4 ključna kvadranta (odgovara anatomiji oka)
    thick_I = get_rim_thickness(0, 1)   # Inferior (Dole)
    thick_S = get_rim_thickness(0, -1)  # Superior (Gore)
    thick_N = get_rim_thickness(-1, 0)  # Nasal (Levo/Desno ka nosu)
    thick_T = get_rim_thickness(1, 0)   # Temporal (Ka slepoočnici)

    # ISNT pravilo: Kod zdravog oka debljina ruba prati odnos Inferior >= Superior >= Nasal >= Temporal
    isnt_valid = (thick_I >= thick_S) and (thick_S >= thick_N) and (thick_N >= thick_T)

    # Heuristička dijagnostika: ako je vCDR preko 0.65 ili je narušeno ISNT pravlo uz povišen vCDR
    if vCDR > 0.65 or (not isnt_valid and vCDR > 0.55):
        diagnosis = "Glaucoma Suspect / Positive"
    else:
        diagnosis = "Healthy"

    # Pakovanje i zaokruživanje rezultata za slanje na Frontend web aplikacije
    results["vCDR"] = round(float(vCDR), 3)
    results["hCDR"] = round(float(hCDR), 3)
    results["aCDR"] = round(float(aCDR), 3)
    results["rim_area_pixels"] = int(rim_area)
    results["isnt_rule_valid"] = bool(isnt_valid)
    results["quadrants_thickness"] = {
        "Inferior": thick_I,
        "Superior": thick_S,
        "Nasal": thick_N,
        "Temporal": thick_T
    }
    results["diagnosis"] = diagnosis

    return results

def calculate_dice_score(pred, target, smooth=1e-6):
    """Numpy evaluaciona funkcija za proveru tačnosti segmentacije na test setu."""
    intersection = np.sum(pred * target)
    union = np.sum(pred) + np.sum(target)
    return (2. * intersection + smooth) / (union + smooth)