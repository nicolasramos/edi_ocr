# Account Invoice Import Simple PDF OCR

Este módulo potencia la importación de facturas PDF en Odoo combinando **OCR avanzado (Tesseract/PaddleOCR)** con **Inteligencia Artificial (Ollama)** para la detección automática de reglas de extracción, además de soportar la asignación de **Cuentas Analíticas**.

## Características Principales

### 1. Extracción de Texto OCR Avanzada
- **Soporte Multi-Motor**: Elige entre **Tesseract** (clásico) o **PaddleOCR** (recomendado para CPU/precisión).
- **Procesamiento de Imágenes**: Extrae texto de facturas escaneadas (imágenes dentro del PDF).
- **Optimización CPU**: PaddleOCR ofrece un excelente rendimiento en servidores sin GPU.

### 2. Detección de Reglas con IA (Ollama)
- **Asistente Inteligente**: Un wizard que analiza el texto de la factura y sugiere automáticamente las expresiones regulares (Regex) para:
    - Número de Factura
    - Fecha de Factura
    - Importe Total
- **Modelos Ligeros**: Optimizado para funcionar con modelos locales pequeños como **Gemma:2b**, **Phi3** o **Llama3.2**.

### 3. Soporte de Contabilidad Analítica
- **Extracción de Analítica**: Capacidad para extraer códigos o nombres de cuentas analíticas del PDF y asignarlos automáticamente a las líneas de la factura (100% distribución).

## Requisitos

### Dependencias de Sistema
- **Poppler Utils**: Necesario para convertir PDF a imágenes (`pdf2image`).
- **Tesseract OCR** (Opcional): Si decides usar el motor Tesseract.
- **Servidor Ollama** (Opcional): Necesario solo si quieres usar la detección automática de reglas con IA.

### Dependencias Python
- `pdf2image`
- `regex`
- `requests` (para conexión con Ollama)
- `paddlepaddle` y `paddleocr` (Recomendado: para usar el motor PaddleOCR)
- `pytesseract` (Opcional: para motor Tesseract)

## Instalación

### 1. Instalar Librerías Python
```bash
# Para PaddleOCR (Recomendado)
pip3 install paddlepaddle paddleocr pdf2image regex requests

# Para Tesseract (Alternativa)
pip3 install pytesseract pdf2image regex requests
```

### 2. Instalar Dependencias del Sistema (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils libgl1-mesa-glx

# Si vas a usar Tesseract:
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa
```

### 3. Instalación de Ollama (Solo para detección con IA)

Si deseas usar la detección automática de reglas, necesitas un servidor Ollama corriendo.

**Opción A: Instalación Local (Linux)**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Opción B: Instalación con Docker (Genérico)**
```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

**Opción C: Integración en Doodba (docker-compose)**

Si usas Doodba, añade el servicio `ollama` a tu archivo `docker-compose.yaml` (o `devel.yaml` / `prod.yaml`):

```yaml
services:
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped

volumes:
  ollama_data:
```

Luego, en la configuración de Odoo (Ajustes), la URL del Endpoint será: `http://ollama:11434/api/generate` (usando el nombre del servicio como host).

### 3. Configure Odoo
1.  Go to **Invoicing > Configuration > Settings**.
2.  Scroll down to **AI Extraction Rules**.
3.  Enter the **Ollama Endpoint** (default: `http://ollama:11434/api/generate`).
4.  Enter the **Ollama Model**:
    *   **Recommended (Balanced)**: `gemma:2b` (Default). Good accuracy, moderate speed.
    *   **Fast (low CPU)**: `llama3.2:1b` or `qwen2.5:0.5b`. Very fast, but might be less accurate with complex regex requests.
    *   **Accurate (slow)**: `llama3.1` or `mistral`. Best results, but slow on CPU.
5.  Click **"Download / Pull Model"** to ensure the model is available in the Ollama container.
6.  (Optional) Customize the **System Prompt** if you need specific extraction logic.

### 4. Configure OCR Engine (Optional)
Puedes descargar los modelos de dos formas:
1.  **Desde Odoo (Nuevo):** Ve a *Ajustes > Facturación > AI Extraction Rules*, introduce el nombre del modelo (ej. `gemma:2b`) y pulsa el botón **"Download / Pull Model"**.
2.  **Desde Consola:** Ejecuta: `docker exec -it <container_id> ollama pull gemma:2b`
```bash
ollama pull gemma:2b
# o
ollama pull phi3
```

## Configuración

Ve a **Ajustes > Facturación > AI Extraction Rules**.

### Configuración de Motor OCR
*   **OCR Engine**: Selecciona `PaddleOCR` (recomendado) o `Tesseract`.
*   **PaddleOCR Language**: Código de idioma si usas Paddle (ej. `en`, `es`).

### Configuración de IA (Ollama)
Para usar el asistente de detección de reglas:
*   **Ollama Endpoint**: URL de tu servidor Ollama (ej. `http://localhost:11434/api/generate`).
*   **Ollama Model**: Modelo a utilizar. Para entornos CPU, recomendamos **`gemma:2b`** o **`phi3`**.

## Uso

### Flujo de Importación (Día a día)
1.  Sube tu factura PDF en **Proveedores > Facturas > Importar**.
2.  El sistema usará el motor OCR configurado (Paddle/Tesseract) para leer el texto.
3.  Aplicará las reglas Regex configuradas en el contacto para extraer los datos.

### Asistente de Detección de Reglas (Configuración inicial por proveedor)
Si tienes un nuevo proveedor y no quieres crear los Regex manualmente:
1.  Ve a la ficha del **Contacto (Partner)**.
2.  Pestaña **Vendor Bills Import**.
3.  Sube un PDF de ejemplo en "Test File".
4.  Haz clic en el botón **"Detect Rules with AI"**.
5.  Confirma la acción. La IA analizará el texto y rellenará los campos de configuración automáticamente.

## Preguntas Frecuentes (FAQ)

### ¿Es necesario Ollama para usar PaddleOCR?
**NO.** Son independientes.
*   **PaddleOCR** es el "ojo": se usa para leer el texto del PDF durante la importación diaria.
*   **Ollama** es el "cerebro": se usa solo puntualmente para ayudarte a configurar las reglas Regex la primera vez.
Puedes usar PaddleOCR para mejorar la lectura de tus facturas sin tener ningún servidor de IA configurado.

### ¿Por qué PaddleOCR en lugar de Tesseract?
PaddleOCR suele ofrecer mucha mejor precisión en facturas con diseños complejos o escaneos de baja calidad, y es sorprendentemente rápido en CPU estándar, lo que lo hace ideal para servidores VPS sin gráfica dedicada.
