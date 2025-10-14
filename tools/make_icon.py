"""
Convierte assets/app_icon.png a assets/app_icon.ico con múltiples tamaños.
Uso: se invoca desde PowerShell antes de crear accesos directos.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
assets = ROOT / 'assets'
png = assets / 'app_icon.png'
ico = assets / 'app_icon.ico'

def main():
    assets.mkdir(parents=True, exist_ok=True)
    if not png.exists():
        print(f"PNG no encontrado: {png}")
        return 1
    img = Image.open(png).convert('RGBA')
    sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
    img.save(ico, sizes=sizes)
    print(f"Icono generado: {ico}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
