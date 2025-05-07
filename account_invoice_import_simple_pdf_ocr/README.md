# Account Invoice Import Simple PDF OCR

Este módulo extiende la funcionalidad del módulo `account_invoice_import_simple_pdf` añadiendo capacidades de OCR (Reconocimiento Óptico de Caracteres) utilizando Tesseract.

## Características

- Extrae texto de facturas PDF que contienen imágenes escaneadas
- Integración con Tesseract OCR para reconocimiento de texto
- Compatible con el flujo de trabajo estándar de importación de facturas
- Soporte para PDF con múltiples páginas
- Funciona con facturas en español (configurable para otros idiomas)

## Requisitos

### Dependencias de sistema

- tesseract-ocr (versión 4.0+)
- tesseract-ocr-spa (paquete de idioma español para Tesseract)
- poppler-utils (para la conversión de PDF a imágenes)

### Dependencias Python

- pytesseract
- pdf2image
- regex
- dateparser
## Instalación

### 1. Instalación del módulo

Puedes instalar este módulo de la misma forma que cualquier otro módulo de Odoo:

1. Clona este repositorio en tu directorio de addons de Odoo
2. Actualiza la lista de aplicaciones en Odoo
3. Busca e instala "Account Invoice Import Simple PDF OCR"

### 2. Instalación de dependencias

Para instalar las dependencias necesarias, ejecuta el script de instalación incluido:

```bash
sudo bash /path/to/odoo/addons/account_invoice_import_simple_pdf_ocr/tools/install_dependencies.sh
```

Alternativamente, puedes instalar las dependencias manualmente:

```bash
# Dependencias del sistema
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils tesseract-ocr-spa

# Dependencias de Python
pip3 install pdf2image pytesseract regex
```

### 3. Configuración de Tesseract

El módulo utiliza por defecto la ruta `/usr/share/tesseract-ocr/4.00/tessdata` como directorio de datos para Tesseract. Si tu instalación utiliza una ruta diferente, deberás modificar la variable `TESSDATA_PREFIX` en el archivo `models/account_invoice_import.py`.

Dependiendo de la versión de Tesseract y la distribución, las rutas pueden variar:
- Tesseract 4.x: `/usr/share/tesseract-ocr/4.00/tessdata`
- Tesseract 5.x: `/usr/share/tesseract-ocr/5/tessdata`

#### Configuración en entornos Docker

Si estás usando Odoo en un contenedor Docker, debes instalar Tesseract dentro del contenedor. Puedes hacerlo de varias formas:

1. **Extendiendo la imagen base de Odoo:**
   - Crea un Dockerfile personalizado que instale las dependencias necesarias
   - Asegúrate de que la variable `TESSDATA_PREFIX` apunte al directorio correcto

2. **En contenedores Doodba:**
   - Modifica el archivo `Dockerfile` de tu proyecto Doodba para incluir las dependencias
   - Usa un script personalizado en `entrypoint.d` para configurar el entorno

Ejemplo para un Dockerfile personalizado:
```Dockerfile
FROM odoo:16

USER root

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
RUN pip3 install pdf2image pytesseract regex

# Verificar la ubicación de tessdata y establecer la variable de entorno
RUN find /usr -name "tessdata" -type d | head -n 1 > /tmp/tessdata_path.txt
ENV TESSDATA_PREFIX=$(cat /tmp/tessdata_path.txt)

USER odoo
```

## Uso

### Importación de facturas

1. Navega a Contabilidad > Proveedores > Facturas
2. Haz clic en "Crear" y luego en "Importar factura"
3. Selecciona un archivo PDF que contenga una factura escaneada
4. El sistema intentará extraer la información utilizando OCR
5. Revisa y confirma los datos extraídos

### Configuración adicional

Para especificar que se use siempre Tesseract como herramienta de extracción de texto:

1. Accede a Ajustes > Parámetros del sistema
2. Crea un nuevo parámetro con:
   - Clave: `invoice_import_simple_pdf.pdf2txt`
   - Valor: `tesseract`

**¿Por qué configurar este parámetro?**

- El módulo base (`account_invoice_import_simple_pdf`) utiliza esta clave para determinar qué herramienta usar para extraer texto de los PDF.
- Las herramientas estándar (`pymupdf`, `pdftotext`, etc.) no pueden leer texto de imágenes.
- Al establecer el valor a `tesseract`, le indicas a Odoo que priorice el uso de Tesseract OCR. Esto es crucial para procesar facturas escaneadas o basadas en imágenes.
- Si no configuras este parámetro, Tesseract solo se usará como último recurso si las otras herramientas fallan. Establecerlo explícitamente asegura que el OCR se intente primero para archivos basados en imágenes.

## Resolución de problemas

### El OCR no reconoce correctamente el texto

- Asegúrate de que el paquete de idioma correcto está instalado para Tesseract
- Verifica que la calidad de la imagen/escáner sea suficiente
- Ajusta la variable `TESSDATA_PREFIX` si es necesario

### El módulo no extrae texto de las imágenes en los PDF

- Verifica que Tesseract esté correctamente instalado: `tesseract --version`
- Comprueba que el parámetro del sistema está configurado: `invoice_import_simple_pdf.pdf2txt` debe tener el valor `tesseract`
- Verifica la ruta de tessdata con: `find /usr -name "tessdata" -type d`
- Comprueba que el usuario que ejecuta Odoo tiene permisos para acceder a tessdata
- Si estás utilizando un contenedor, asegúrate de que todas las dependencias están instaladas dentro del contenedor
- Comprueba los logs del servidor para ver si hay errores específicos de Tesseract

### Error de importación de módulos Python

Si encuentras errores relacionados con la importación de módulos Python:

```python
ImportError: No module named pytesseract
```

Asegúrate de que las dependencias de Python estén instaladas correctamente:

```bash
pip3 install pdf2image pytesseract regex
```

## Pruebas

Este módulo incluye pruebas automatizadas que verifican:

1. Extracción de texto mediante OCR de facturas escaneadas
2. Funcionamiento del método fallback para interpretar facturas
3. Selección específica de herramientas de extracción

Para ejecutar las pruebas:

```bash
odoo -d your_database -i account_invoice_import_simple_pdf_ocr --test-enable
```

## Soporte

Para obtener ayuda sobre este módulo, contactar a:

   - Nicolás Ramos <hola@nicolasramos.es>

## Licencia

LGPL-3
