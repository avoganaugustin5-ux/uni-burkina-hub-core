import sys
sys.path.insert(0, '.')
import main
from pathlib import Path

chemin = Path(r'C:\Users\Augustin AVOGAN\Downloads\Mobile Devices\IMG_20260524_172031_718.jpg')
print('Image existe:', chemin.exists())
texte = main.ocr_image(chemin, 'fra')
if texte:
    print('Texte extrait:', repr(texte[:300]))
else:
    print('VIDE — aucun texte extrait')
