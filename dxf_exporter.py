# -*- coding: utf-8 -*-
"""
dxf_exporter.py  —  Motor de exportación QGIS → DXF
Una capa DXF por cada valor único del campo de categoría.
"""
import math

# ezdxf se importa de forma diferida para no bloquear el arranque del plugin
_ezdxf = None
_TEA = None


def _vendor_dir():
    """Carpeta propia del plugin donde se instala ezdxf si no está ya
    disponible en el Python de QGIS. Al estar siempre dentro de la carpeta
    del plugin (en AppData/Roaming, o el equivalente en Linux/Mac), nunca
    hay problemas de permisos de escritura, y al añadirla nosotros mismos a
    sys.path no depende de que el "user site-packages" de Python esté
    habilitado (site.ENABLE_USER_SITE), que en el intérprete embebido de
    QGIS suele venir desactivado — esta es la causa real de que antes la
    instalación con --user "funcionara" (pip devolvía código 0) pero el
    siguiente import ezdxf siguiera fallando.
    """
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '_vendor')


def _ensure_ezdxf():
    global _ezdxf, _TEA
    if _ezdxf is not None:
        return

    import sys
    import os
    import importlib

    vendor = _vendor_dir()
    if os.path.isdir(vendor) and vendor not in sys.path:
        sys.path.insert(0, vendor)

    try:
        import ezdxf
        from ezdxf.enums import TextEntityAlignment as TEA
        _ezdxf = ezdxf
        _TEA = TEA
        return
    except ImportError:
        pass

    _install_ezdxf(vendor)

    # Tras instalar, hay que asegurarse de que Python reconoce la carpeta
    # como recién poblada (invalidar cachés de import) y que sigue en
    # sys.path antes de reintentar.
    importlib.invalidate_caches()
    if vendor not in sys.path:
        sys.path.insert(0, vendor)

    try:
        import ezdxf
        from ezdxf.enums import TextEntityAlignment as TEA
        _ezdxf = ezdxf
        _TEA = TEA
    except ImportError as e:
        raise RuntimeError(
            "ezdxf se ha instalado pero QGIS todavía no lo encuentra.\n\n"
            "Cierra QGIS por completo y vuelve a abrirlo; si el problema "
            "persiste, instálalo manualmente desde la consola OSGeo4W:\n"
            "  python -m pip install ezdxf\n\n"
            f"Detalle: {e}"
        ) from e


def _install_ezdxf(vendor_dir):
    import subprocess  # nosec B404 - used with shell=False and a fixed argument list only
    import sys
    import os
    import glob

    exe = sys.executable
    # En QGIS Windows el ejecutable es qgis.exe; buscamos python.exe en apps/Python3*
    if 'python' not in os.path.basename(exe).lower():
        parent = os.path.dirname(os.path.dirname(exe))
        hits = sorted(glob.glob(os.path.join(parent, 'apps', 'Python3*')), reverse=True)
        for hit in hits:
            candidate = os.path.join(hit, 'python.exe')
            if os.path.isfile(candidate):
                exe = candidate
                break

    os.makedirs(vendor_dir, exist_ok=True)

    # Se instala con --target en una carpeta propia del plugin en vez de
    # con --user: así no hace falta ser administrador (la carpeta del
    # plugin siempre es escribible) y no depende de que el "user site" de
    # Python esté habilitado en el intérprete embebido de QGIS. En Linux,
    # algunas distribuciones (Ubuntu/Debian 23.04+) rechazan igualmente la
    # instalación salvo que se indique --break-system-packages, así que se
    # prueba primero sin la bandera y, si falla, con ella.
    attempts = [
        [],
        ['--break-system-packages'],
    ]

    last_output = ""
    for flags in attempts:
        cmd = ([exe, '-m', 'pip', 'install', '--quiet', '--upgrade',
                '--target', vendor_dir, 'ezdxf'] + flags)
        try:
            # "exe" is resolved above from sys.executable / a local QGIS
            # Python installation path, not from any external or
            # user-supplied input; the rest of the command is a fixed list
            # of literals, and shell=False (the default) is used, so there
            # is no shell-injection surface here.
            result = subprocess.run(  # nosec B603 B607
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=False,
            )
            if result.returncode == 0:
                return
            last_output = result.stdout or ""

        except Exception as e:
            last_output = str(e)

    raise RuntimeError(
        "No se pudo instalar ezdxf automáticamente.\n\n"
        "Instálalo manualmente:\n"
        "  - Windows (OSGeo4W Shell, como Administrador):\n"
        "      python -m pip install ezdxf\n"
        "  - Linux:\n"
        "      python3 -m pip install ezdxf --break-system-packages\n"
        "    (o crea un entorno virtual e indícaselo a QGIS)\n\n"
        f"Comando probado: {exe} -m pip install --target {vendor_dir} ezdxf\n"
        f"Detalle del último intento:\n{last_output.strip()[-800:]}"
    )


# ── Helpers de color ──────────────────────────────────────────────────────────

def _qcolor_to_aci(qcolor):
    """Convierte QColor al índice de color ACI más cercano (fallback)."""
    r, g, b = qcolor.red(), qcolor.green(), qcolor.blue()

    # Tabla ACI ampliada con más colores para mejor aproximación
    _ACI = [
        # Rojo y variantes
        (255, 0, 0, 1),       # Rojo puro
        (200, 0, 0, 13),      # Rojo oscuro 1
        (180, 0, 0, 11),      # Rojo oscuro 2
        (255, 100, 0, 30),    # Rojo anaranjado
        (255, 150, 0, 40),    # Naranja

        # Verde y variantes
        (0, 255, 0, 3),       # Verde puro
        (100, 200, 0, 93),    # Verde lima
        (0, 150, 0, 92),      # Verde oscuro 1
        (0, 100, 0, 91),      # Verde oscuro 2

        # Azul y variantes
        (0, 0, 255, 5),       # Azul puro
        (100, 150, 255, 37),  # Azul cielo
        (0, 100, 255, 36),    # Azul brillante
        (0, 0, 180, 25),      # Azul oscuro
        (0, 0, 128, 174),     # Azul marino

        # Cyan
        (0, 255, 255, 4),     # Cyan puro
        (100, 200, 255, 50),  # Cyan claro
        (0, 180, 200, 45),    # Cyan oscuro

        # Magenta/Rosa
        (255, 0, 255, 6),     # Magenta puro
        (255, 150, 200, 20),  # Rosa
        (200, 50, 150, 19),   # Magenta oscuro

        # Amarillo
        (255, 255, 0, 2),     # Amarillo puro
        (200, 200, 0, 52),    # Amarillo oscuro
        (255, 200, 0, 51),    # Amarillo claro

        # Grises
        (255, 255, 255, 7),   # Blanco
        (220, 220, 220, 254),  # Gris muy claro
        (192, 192, 192, 9),   # Gris claro
        (150, 150, 150, 251),  # Gris medio
        (128, 128, 128, 8),   # Gris oscuro
        (64, 64, 64, 252),    # Gris muy oscuro
        (0, 0, 0, 250),       # Negro

        # Marrones y naranjas
        (165, 42, 42, 12),    # Marrón
        (180, 100, 50, 53),   # Marrón claro
        (200, 150, 100, 54),  # Beige

        # Otros
        (0, 128, 128, 134),   # Teal
        (128, 0, 128, 218),   # Morado
        (100, 0, 100, 215),   # Morado oscuro
        (150, 100, 150, 217),  # Púrpura
    ]

    best_aci = 7
    best_dist = float('inf')
    for (cr, cg, cb, aci) in _ACI:
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < best_dist:
            best_dist = d
            best_aci = aci
    return best_aci


def _color_attribs(qcolor):
    """Devuelve un dict listo para dxfattribs con el color EXACTO (true_color)
    y un ACI de respaldo para visores muy antiguos que no soporten true_color.

    IMPORTANTE: en ezdxf el atributo 'color' (código DXF 62) es SIEMPRE un
    índice ACI (entero 0-256), nunca una tupla RGB. Pasarle una tupla
    (como se hacía antes) provoca un TypeError interno y el código caía
    siempre al 'fallback' de ACI aproximado, por lo que el color real
    JAMÁS se llegaba a aplicar. La forma correcta de tener el color RGB
    exacto en DXF es el atributo 'true_color' (código 420), independiente
    de 'color'.
    """
    if qcolor is None:
        return {'color': 7}
    r, g, b = qcolor.red(), qcolor.green(), qcolor.blue()
    aci = _qcolor_to_aci(qcolor)
    return {'color': aci, 'true_color': _ezdxf.colors.rgb2int((r, g, b))}


def _lw_to_dxf(qgis_lw_mm):
    """Convierte grosor QGIS (mm) al lineweight DXF más cercano (centésimas de mm)."""
    _LW_TABLE = [0, 5, 9, 13, 15, 18, 20, 25, 30, 35, 40, 50, 53,
                 60, 70, 80, 90, 100, 106, 120, 140, 158, 200, 211]
    target = int(round(qgis_lw_mm * 100))
    return min(_LW_TABLE, key=lambda x: abs(x - target))


def _ltype_name(qt_pen_style):
    """Mapea Qt PenStyle (int) al nombre de tipo de línea DXF."""
    # Valores numéricos: SolidLine=1, DashLine=2, DotLine=3, DashDotLine=4, DashDotDotLine=5
    _MAP = {
        1: 'Continuous',
        2: 'DASHED',
        3: 'DOTTED',
        4: 'DASHDOT',
        5: 'DIVIDE',
    }
    # En Qt6 el enum no es convertible con int() directamente, usar .value
    try:
        val = qt_pen_style.value
    except AttributeError:
        val = int(qt_pen_style)
    return _MAP.get(val, 'Continuous')


# ── Lectura de simbología QGIS ────────────────────────────────────────────────

def _get_label_settings(qgis_layer):
    """Devuelve el QgsPalLayerSettings activo de la capa (el de la primera
    regla, si el etiquetado es "basado en reglas"), o None si la capa no
    tiene etiquetado configurado."""
    try:
        labeling = qgis_layer.labeling()
    except Exception:
        return None
    if labeling is None:
        return None

    try:
        from qgis.core import QgsRuleBasedLabeling
        if isinstance(labeling, QgsRuleBasedLabeling):
            for child in labeling.rootRule().children():
                try:
                    s = child.settings()
                    if s is not None:
                        return s
                except Exception:
                    continue
            return None
    except Exception:
        pass

    try:
        return labeling.settings()
    except Exception:
        return None


def _label_rotation_for_feature(label_settings, feat, ctx, geom):
    """Ángulo (grados, sentido antihorario, 0 = horizontal) con el que se
    debe escribir el texto exportado a DXF para conservar, en la medida
    de lo posible, la orientación que tiene en QGIS:

    1) Si el etiquetado tiene una rotación por datos (campo/expresión de
       "Rotación"), se usa ese valor tal cual.
    2) Si no, y la geometría es una línea (calles, viales...), se
       aproxima con el ángulo del propio tramo en el punto donde se
       coloca el texto — igual que la colocación "Paralela a la línea"
       de QGIS —, ajustado para que el texto no quede boca abajo.
    3) En cualquier otro caso, 0 (horizontal), como antes.

    Nota: la colocación "Curva" de QGIS (texto siguiendo la curvatura de
    la línea, letra a letra) no tiene equivalente en una entidad TEXT de
    DXF; aquí se aproxima con un único ángulo recto, que es lo que
    cualquier CAD puede representar.
    """
    import math

    if label_settings is not None:
        try:
            from qgis.core import QgsPalLayerSettings
            props = label_settings.dataDefinedProperties()
            if props.isActive(QgsPalLayerSettings.Property.LabelRotation):
                ctx.expressionContext().setFeature(feat)
                val, ok = props.value(QgsPalLayerSettings.Property.LabelRotation,
                                       ctx.expressionContext())
                if ok and val is not None:
                    # QGIS mide la rotación en sentido horario; DXF en
                    # antihorario (igual que con los símbolos de punto).
                    return -float(val)
        except Exception:
            pass

    try:
        from qgis.core import QgsWkbTypes
        if geom is None or geom.isEmpty():
            return 0.0
        if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.GeometryType.LineGeometry:
            return 0.0

        if geom.isMultipart():
            parts = geom.asMultiPolyline()
            pts = max(parts, key=len) if parts else None
        else:
            pts = geom.asPolyline()
        if not pts or len(pts) < 2:
            return 0.0

        centroid = geom.centroid().asPoint()
        best_d = None
        best_ang = 0.0
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]
            mx, my = (p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2
            d = (mx - centroid.x()) ** 2 + (my - centroid.y()) ** 2
            if best_d is None or d < best_d:
                best_d = d
                ang = math.degrees(math.atan2(p2.y() - p1.y(), p2.x() - p1.x()))
                # Nunca boca abajo: se mantiene siempre legible de
                # izquierda a derecha (entre -90° y 90°).
                if ang > 90:
                    ang -= 180
                elif ang < -90:
                    ang += 180
                best_ang = ang
        return best_ang
    except Exception:
        return 0.0


def _rule_based_symbol_for_feature(renderer, feat, ctx):
    """Empareja manualmente las reglas de un QgsRuleBasedRenderer con la
    entidad, IGNORANDO el rango de escala de cada regla.

    renderer.symbolForFeature() puede devolver None para renderers "Basado
    en reglas" cuando se ejecuta fuera del pipeline normal de dibujado del
    lienzo (como aquí, en un hilo de exportación): qué reglas están
    "activas" depende de la escala que trae el contexto, y si ninguna
    regla activa cubre esa escala concreta no se devuelve ningún símbolo
    — incluso si hay una regla sin ninguna restricción de escala, como
    suele ser la regla "base" de un estilo con sombra (p.ej. "Building"
    sin límite de escala + "Shadow 1/2/3" limitadas a un rango estrecho
    para simular la sombra solo al hacer zoom).

    Un DXF no tiene "escala de visualización": es un dibujo a coordenadas
    reales, así que aquí basta con comprobar el filtro (expresión) de cada
    regla, exactamente igual que si se imprimiera/exportara a una escala
    fija; se ignora a propósito el rango de escala.
    """
    from qgis.core import QgsRuleBasedRenderer, QgsExpression

    if not isinstance(renderer, QgsRuleBasedRenderer):
        return None

    try:
        ctx.expressionContext().setFeature(feat)
    except Exception:
        pass

    def _walk(rule):
        for child in rule.children():
            try:
                if not child.active():
                    continue
            except Exception:
                pass

            matched = True
            filt = child.filterExpression()
            if filt and filt.strip().upper() != 'ELSE':
                try:
                    expr = QgsExpression(filt)
                    expr.prepare(ctx.expressionContext())
                    matched = bool(expr.evaluate(ctx.expressionContext()))
                except Exception:
                    # Si la expresión no se puede evaluar aquí, no se
                    # descarta la regla por eso: mejor un color aproximado
                    # que ninguno.
                    matched = True

            if not matched:
                continue

            sym = child.symbol()
            if sym is not None:
                return sym
            nested = _walk(child)
            if nested is not None:
                return nested

        return None

    return _walk(renderer.rootRule())


def _symbol_props(qgis_symbol):
    """Extrae color, grosor y tipo de línea de un QgsSymbol."""
    from qgis.core import QgsSimpleLineSymbolLayer, QgsSimpleFillSymbolLayer, QgsSimpleMarkerSymbolLayer
    props = {
        'color': None,
        'fill_color': None,
        'linewidth_mm': 0.25,
        'linestyle': 'Continuous',
        'marker_size': 1.0,
        'marker_shape': 'circle',
        'marker_angle': 0.0,
    }
    if qgis_symbol is None:
        return props

    color = qgis_symbol.color()
    if color is not None and color.isValid():
        props['color'] = color
        props['fill_color'] = color  # fallback: color principal también como relleno

    for i in range(qgis_symbol.symbolLayerCount()):
        sl = qgis_symbol.symbolLayer(i)
        if isinstance(sl, QgsSimpleLineSymbolLayer):
            props['color'] = sl.color()
            props['linewidth_mm'] = sl.width()
            props['linestyle'] = _ltype_name(sl.penStyle())
        elif isinstance(sl, QgsSimpleFillSymbolLayer):
            props['fill_color'] = sl.fillColor()
            props['color'] = sl.strokeColor()
            props['linewidth_mm'] = sl.strokeWidth()
        elif isinstance(sl, QgsSimpleMarkerSymbolLayer):
            props['color'] = sl.color()
            props['marker_size'] = sl.size()
            props['marker_shape'] = _marker_shape_name(sl)
            try:
                props['marker_angle'] = sl.angle()
            except Exception:
                props['marker_angle'] = 0.0
        else:
            # Tipos de relleno "avanzados" (degradado, shapeburst, textura,
            # patrón de puntos/líneas, relleno de centroide con marcador...)
            # no son instancias de QgsSimpleFillSymbolLayer, así que caían
            # fuera de todos los "elif" anteriores y no aportaban ningún
            # color propio: fill_color se quedaba con lo que hubiera puesto
            # qgis_symbol.color() más arriba (a veces un color por defecto
            # sin inicializar → negro). Casi todos estos tipos de capa sí
            # exponen ALGÚN color reconocible a través de fillColor(),
            # color() o subSymbol().color(); se prueba cada uno y se usa
            # el primero que dé un color válido y no transparente.
            fc = None
            for getter in ('fillColor', 'color'):
                fn = getattr(sl, getter, None)
                if callable(fn):
                    try:
                        c = fn()
                        if c is not None and c.isValid() and c.alpha() > 0:
                            fc = c
                            break
                    except Exception:
                        pass
            if fc is None:
                sub = getattr(sl, 'subSymbol', None)
                if callable(sub):
                    try:
                        sub_symbol = sub()
                        if sub_symbol is not None:
                            c = sub_symbol.color()
                            if c is not None and c.isValid() and c.alpha() > 0:
                                fc = c
                    except Exception:
                        pass
            if fc is not None:
                props['fill_color'] = fc
                if props['color'] is None:
                    props['color'] = fc

            sc = None
            for getter in ('strokeColor', 'outlineColor', 'color'):
                fn = getattr(sl, getter, None)
                if callable(fn):
                    try:
                        c = fn()
                        if c is not None and c.isValid() and c.alpha() > 0:
                            sc = c
                            break
                    except Exception:
                        pass
            if sc is not None:
                props['color'] = sc

    return props



# ── Bloques de símbolo (marcador QGIS → bloque DXF) ───────────────────────────

# Mapea el nombre de forma de QGIS (Qgis.MarkerShape / QgsSimpleMarkerSymbolLayerBase.Shape)
# a una de las formas básicas que sabemos dibujar en un bloque DXF.
_SHAPE_MAP = {
    'circle': 'circle', 'semicircle': 'circle', 'thirdcircle': 'circle',
    'quartercircle': 'circle', 'halfarc': 'circle', 'thirdarc': 'circle',
    'quarterarc': 'circle',
    'square': 'square', 'roundedsquare': 'square', 'trapezoid': 'square',
    'diamond': 'diamond', 'diamondstar': 'diamond',
    'pentagon': 'pentagon', 'shield': 'pentagon',
    'hexagon': 'hexagon',
    'triangle': 'triangle', 'equilateraltriangle': 'triangle',
    'arrow': 'triangle', 'arrowhead': 'triangle', 'arrowheadfilled': 'triangle',
    'star': 'star',
    'cross': 'cross', 'crossfill': 'cross', 'line': 'cross',
    'cross2': 'x',
}


def _marker_shape_name(symbol_layer):
    """Nombre de forma normalizado ('circle', 'square', ...) a partir de un
    QgsSimpleMarkerSymbolLayer. Si no se reconoce (p.ej. iconos SVG/raster,
    que no son formas simples), se usa 'circle' como aproximación genérica."""
    try:
        shape = symbol_layer.shape()
        raw = getattr(shape, 'name', None) or str(shape).rsplit('.', 1)[-1]
        return _SHAPE_MAP.get(raw.lower(), 'circle')
    except Exception:
        return 'circle'


def _draw_marker_shape(block, shape):
    """Dibuja la forma básica dentro de un BLOCK, inscrita en un círculo de
    radio 0.5 (es decir, diámetro 1 unidad de dibujo), centrada en (0,0).
    Color = 0 (BYBLOCK) para que cada INSERT pueda darle su propio color
    (el de la simbología QGIS de esa categoría) sin duplicar el bloque."""
    attrs = {'color': 0}
    r = 0.5
    if shape == 'circle':
        block.add_circle((0, 0), radius=r, dxfattribs=attrs)
    elif shape == 'square':
        pts = [(-r, -r), (r, -r), (r, r), (-r, r)]
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'diamond':
        pts = [(0, r), (r, 0), (0, -r), (-r, 0)]
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'triangle':
        pts = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
               for a in (90, 210, 330)]
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'pentagon':
        pts = [(r * math.cos(math.radians(90 + 72 * i)), r * math.sin(math.radians(90 + 72 * i)))
               for i in range(5)]
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'hexagon':
        pts = [(r * math.cos(math.radians(90 + 60 * i)), r * math.sin(math.radians(90 + 60 * i)))
               for i in range(6)]
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'star':
        r_in = r * 0.382
        pts = []
        for i in range(10):
            ang = math.radians(90 + 36 * i)
            rad = r if i % 2 == 0 else r_in
            pts.append((rad * math.cos(ang), rad * math.sin(ang)))
        block.add_lwpolyline(pts, close=True, dxfattribs=attrs)
    elif shape == 'cross':
        block.add_line((-r, 0), (r, 0), dxfattribs=attrs)
        block.add_line((0, -r), (0, r), dxfattribs=attrs)
    elif shape == 'x':
        block.add_line((-r, -r), (r, r), dxfattribs=attrs)
        block.add_line((-r, r), (r, -r), dxfattribs=attrs)
    else:
        block.add_circle((0, 0), radius=r, dxfattribs=attrs)


# ── Exportador principal ──────────────────────────────────────────────────────

class DXFExporter:
    """
    Exporta una lista de capas QGIS a un único archivo DXF.
    Cada valor único del campo de categoría → una capa DXF.
    """

    def __init__(self, output_path, target_crs=None, progress_cb=None,
                 map_settings=None, extent=None, extent_crs=None):
        """
        map_settings: QgsMapSettings del lienzo actual de QGIS (opcional).
                        Si se indica, se usa para construir un
                        QgsRenderContext real (con extensión y escala
                        válidas), imprescindible para que renderers
                        "Basado en reglas" con filtros de escala u
                        expresiones resuelvan bien el símbolo. Sin esto,
                        symbolForFeature() puede devolver None y el color
                        cae al negro por defecto.
        extent/extent_crs: si se indican, solo se exportan las entidades
                        que intersecan esa extensión (p.ej. la vista
                        actual del lienzo), independientemente de si la
                        capa tiene o no un filtro (subset string) propio.
        """
        _ensure_ezdxf()
        self.output_path = output_path
        self.target_crs = target_crs
        self.progress_cb = progress_cb or (lambda v, msg: None)
        self.map_settings = map_settings
        self.extent = extent
        self.extent_crs = extent_crs

        self.doc = _ezdxf.new('R2010', setup=True)
        self.msp = self.doc.modelspace()
        self._created_layers = set()
        self._marker_blocks = {}

        # Tipos de línea estándar
        for lt in ('DASHED', 'DOTTED', 'DASHDOT', 'DIVIDE'):
            try:
                self.doc.linetypes.add(lt, pattern=[0.5, -0.25])
            except _ezdxf.DXFTableEntryError:
                # El tipo de línea ya existe en la plantilla base de ezdxf
                # (algunos vienen predefinidos según la versión); no es un
                # error real, simplemente no hace falta volver a crearlo.
                pass

    # ── Capa DXF ──────────────────────────────────────────────────────────────

    def _ensure_layer(self, name, qcolor, lw_dxf=25, ltype='Continuous'):
        # Saneamos el nombre a fondo: ezdxf/AutoCAD prohíben ciertos
        # caracteres en nombres de capa (< > / \ " : ; ? * | , = ` y
        # caracteres de control) y no admiten nombre vacío. Si el campo de
        # categoría trae valores "raros" (None, números, espacios, comas...)
        # esto evita que ezdxf lance una excepción y aborte TODO el DXF.
        import re
        raw = '' if name is None else str(name)
        safe_name = re.sub(r'[<>/\\":;?*|,=`\x00-\x1f]', '_', raw).strip()
        safe_name = safe_name.rstrip('.') or 'SIN_NOMBRE'
        # AutoCAD limita el nombre de capa a 255 caracteres.
        safe_name = safe_name[:255]
        if safe_name not in self._created_layers:
            try:
                lyr = self.doc.layers.new(safe_name)
            except Exception:
                try:
                    lyr = self.doc.layers.get(safe_name)
                except Exception:
                    # Última red de seguridad: si ni siquiera existe ya,
                    # usamos un nombre genérico para no perder la entidad.
                    safe_name = 'CAPA_SIN_NOMBRE'
                    if safe_name not in self._created_layers:
                        lyr = self.doc.layers.new(safe_name)
                    else:
                        lyr = self.doc.layers.get(safe_name)

            aci = _qcolor_to_aci(qcolor) if qcolor else 7
            lyr.color = aci  # ACI de respaldo (entero, único formato válido aquí)
            if qcolor:
                try:
                    # color exacto de verdad: propiedad .rgb (gestiona el true_color)
                    lyr.rgb = (qcolor.red(), qcolor.green(), qcolor.blue())
                except (TypeError, ValueError, AttributeError):
                    # QColor con canales inválidos o no inicializados: nos
                    # quedamos con el color ACI de respaldo ya asignado arriba.
                    pass

            lyr.dxf.lineweight = lw_dxf
            lyr.linetype = ltype
            self._created_layers.add(safe_name)
        return safe_name

    # ── Transformador de coordenadas ──────────────────────────────────────────

    def _get_transform(self, layer):
        from qgis.core import QgsCoordinateTransform, QgsProject
        if self.target_crs and layer.crs() != self.target_crs:
            return QgsCoordinateTransform(layer.crs(), self.target_crs, QgsProject.instance())
        return None

    def _pt(self, geom_pt, transform):
        if transform:
            p = transform.transform(geom_pt)
            return (p.x(), p.y(), 0.0)
        return (geom_pt.x(), geom_pt.y(), 0.0)

    # ── Geometría → entidades DXF ─────────────────────────────────────────────

    def _add_point(self, pt, layer_name, props):
        x, y = pt[0], pt[1]
        attrs = {'layer': layer_name}
        attrs.update(_color_attribs(props.get('color')))
        self.msp.add_point((x, y), dxfattribs=attrs)

    # ── Símbolo QGIS como bloque DXF (INSERT) ─────────────────────────────────

    def _get_or_create_marker_block(self, shape):
        shape = shape or 'circle'
        if shape not in self._marker_blocks:
            block_name = f'SIMBOLO_{shape.upper()}'
            if block_name in self.doc.blocks:
                self._marker_blocks[shape] = block_name
            else:
                block = self.doc.blocks.new(name=block_name)
                _draw_marker_shape(block, shape)
                self._marker_blocks[shape] = block_name
        return self._marker_blocks[shape]

    def _add_symbol_block(self, pt, layer_name, props, symbol_size):
        x, y = pt[0], pt[1]
        shape = props.get('marker_shape', 'circle')
        block_name = self._get_or_create_marker_block(shape)
        angle = props.get('marker_angle', 0.0) or 0.0
        attrs = {
            'layer': layer_name,
            'xscale': symbol_size,
            'yscale': symbol_size,
            # QGIS gira en sentido horario; DXF en sentido antihorario.
            'rotation': -angle,
        }
        attrs.update(_color_attribs(props.get('color')))
        self.msp.add_blockref(block_name, (x, y), dxfattribs=attrs)

    def _add_polyline(self, points, layer_name, props, closed=False):
        if len(points) < 2:
            return
        lw = _lw_to_dxf(props.get('linewidth_mm', 0.25))
        attrs = {'layer': layer_name, 'lineweight': lw}
        attrs.update(_color_attribs(props.get('color')))
        pts2d = [(p[0], p[1]) for p in points]
        self.msp.add_lwpolyline(pts2d, dxfattribs=attrs, close=closed)

    def _add_hatch(self, exterior, holes, layer_name, props, pattern='SOLID', scale=1.0):
        fill_color = props.get('fill_color') or props.get('color')
        if fill_color is None or fill_color.alpha() < 10:
            return

        r, g, b = fill_color.red(), fill_color.green(), fill_color.blue()
        aci = _qcolor_to_aci(fill_color)

        hatch = self.msp.add_hatch(dxfattribs={'layer': layer_name})
        if not pattern or pattern == 'SOLID':
            hatch.set_solid_fill(color=aci, rgb=(r, g, b))
        else:
            try:
                hatch.set_pattern_fill(pattern, color=aci, scale=scale)
                # set_pattern_fill solo admite color ACI; el color real (RGB)
                # se asigna aparte para que coincida con el de QGIS.
                hatch.rgb = (r, g, b)
            except Exception:
                # Nombre de patrón no reconocido por ezdxf: se recurre al
                # relleno sólido para no perder la exportación de la capa.
                hatch.set_solid_fill(color=aci, rgb=(r, g, b))

        # Contorno exterior
        ext2d = [(p[0], p[1]) for p in exterior]
        if ext2d:
            hatch.paths.add_polyline_path(ext2d, is_closed=True)
        # Agujeros
        for hole in holes:
            h2d = [(p[0], p[1]) for p in hole]
            if h2d:
                hatch.paths.add_polyline_path(h2d, is_closed=True, flags=1)

    def _add_text(self, text, x, y, height, layer_name, qcolor, rotation=0.0):
        attrs = {'layer': layer_name, 'height': height, 'insert': (x, y)}
        if rotation:
            attrs['rotation'] = rotation
        attrs.update(_color_attribs(qcolor))
        self.msp.add_text(str(text), dxfattribs=attrs)

    # ── Procesar geometría de una feature ────────────────────────────────────

    def _process_geometry(self, geom, transform, layer_name, props, geom_type, export_hatch=True,
                          export_symbol_block=False, symbol_size=1.0,
                          outline_uses_fill_color=True, hatch_pattern='SOLID', hatch_scale=1.0):
        from qgis.core import QgsWkbTypes
        if geom is None or geom.isEmpty():
            return

        wkb_type = QgsWkbTypes.flatType(geom.wkbType())

        # Puntos
        if wkb_type == QgsWkbTypes.Type.Point:
            pt = geom.asPoint()
            tp = self._pt(pt, transform)
            self._add_point(tp, layer_name, props)
            if export_symbol_block:
                self._add_symbol_block(tp, layer_name, props, symbol_size)

        elif wkb_type == QgsWkbTypes.Type.MultiPoint:
            for pt in geom.asMultiPoint():
                tp = self._pt(pt, transform)
                self._add_point(tp, layer_name, props)
                if export_symbol_block:
                    self._add_symbol_block(tp, layer_name, props, symbol_size)

        # Líneas
        elif wkb_type == QgsWkbTypes.Type.LineString:
            pts = [self._pt(p, transform) for p in geom.asPolyline()]
            self._add_polyline(pts, layer_name, props)

        elif wkb_type == QgsWkbTypes.Type.MultiLineString:
            for line in geom.asMultiPolyline():
                pts = [self._pt(p, transform) for p in line]
                self._add_polyline(pts, layer_name, props)

        # Polígonos
        elif wkb_type == QgsWkbTypes.Type.Polygon:
            poly = geom.asPolygon()
            if not poly:
                return
            ext = [self._pt(p, transform) for p in poly[0]]
            holes = [[self._pt(p, transform) for p in ring] for ring in poly[1:]]
            if export_hatch:
                self._add_hatch(ext, holes, layer_name, props, hatch_pattern, hatch_scale)
            outline_props = props
            if outline_uses_fill_color and props.get('fill_color') is not None:
                # El contorno hereda el color de relleno: en simbología
                # "Categorizado" lo habitual es que solo varíe el relleno,
                # quedando el borde con el gris por defecto de QGIS; en DXF
                # ese borde es lo que más se ve, así que por defecto se
                # unifica con el color del relleno (la capa).
                outline_props = dict(props)
                outline_props['color'] = props['fill_color']
            self._add_polyline(ext, layer_name, outline_props, closed=True)
            for hole in holes:
                self._add_polyline(hole, layer_name, outline_props, closed=True)

        elif wkb_type == QgsWkbTypes.Type.MultiPolygon:
            for poly in geom.asMultiPolygon():
                if not poly:
                    continue
                ext = [self._pt(p, transform) for p in poly[0]]
                holes = [[self._pt(p, transform) for p in ring] for ring in poly[1:]]
                if export_hatch:
                    self._add_hatch(ext, holes, layer_name, props, hatch_pattern, hatch_scale)
                outline_props = props
                if outline_uses_fill_color and props.get('fill_color') is not None:
                    outline_props = dict(props)
                    outline_props['color'] = props['fill_color']
                self._add_polyline(ext, layer_name, outline_props, closed=True)
                for hole in holes:
                    self._add_polyline(hole, layer_name, outline_props, closed=True)

    # ── API pública ───────────────────────────────────────────────────────────

    def add_layer(self, qgis_layer, category_field=None, label_field=None,
                  label_height=2.0, export_labels=True, export_hatch=True,
                  export_symbol_block=False, symbol_size=1.0,
                  outline_uses_fill_color=True, hatch_pattern='SOLID', hatch_scale=1.0):
        """
        Procesa una capa QGIS completa.
        category_field: campo cuyo valor se usa como nombre de capa DXF.
                        Si None, se usa el nombre de la capa QGIS.
        export_symbol_block: además del punto, inserta un bloque DXF con una
                        aproximación del símbolo de QGIS (círculo, cuadrado,
                        triángulo, cruz, X, estrella, pentágono, hexágono...).
        symbol_size: tamaño del bloque insertado, en unidades del mapa (no
                        tiene relación con el tamaño en mm/px de QGIS, que es
                        un tamaño de pantalla y no de mundo real).
        outline_uses_fill_color: en polígonos, el contorno usa el mismo color
                        que el relleno en vez del color de borde por defecto
                        de QGIS (típicamente un gris fijo independiente de la
                        categoría). Esto es lo que casi siempre se quiere
                        cuando se usa un renderer "Categorizado" con colores
                        aleatorios, ya que ahí solo el relleno varía.
        """
        from qgis.core import QgsVectorLayer, QgsRenderContext, QgsFeatureRequest

        if not isinstance(qgis_layer, QgsVectorLayer):
            return

        renderer = qgis_layer.renderer()
        transform = self._get_transform(qgis_layer)

        # ── Filtro y recorte por extensión (p.ej. la vista actual del
        #    lienzo) ─────────────────────────────────────────────────────
        # Independiente de si la capa tiene o no un filtro (subset string)
        # propio: esto permite exportar "solo lo que se ve" aunque la capa
        # en cuestión no tenga configurado ningún filtro por municipio.
        # setFilterRect() solo descarta entidades que NO tocan la
        # extensión; una entidad que la toca pero se sale por un lado se
        # sigue exportando ENTERA. Por eso además se recorta la geometría
        # de cada entidad a este rectángulo (clip_geom) más abajo.
        request = QgsFeatureRequest()
        clip_geom = None
        if self.extent is not None:
            ext = self.extent
            if self.extent_crs is not None and qgis_layer.crs() != self.extent_crs:
                from qgis.core import QgsCoordinateTransform, QgsProject
                ext_transform = QgsCoordinateTransform(
                    self.extent_crs, qgis_layer.crs(), QgsProject.instance())
                try:
                    ext = ext_transform.transformBoundingBox(ext)
                except Exception:
                    pass
            request.setFilterRect(ext)
            from qgis.core import QgsGeometry
            clip_geom = QgsGeometry.fromRect(ext)
        features = list(qgis_layer.getFeatures(request))
        total = len(features)

        # Contexto de renderizado necesario para symbolForFeature. Se
        # construye a partir del QgsMapSettings real del lienzo cuando está
        # disponible: un QgsRenderContext() vacío (sin extensión ni escala)
        # hace que renderers "Basado en reglas" con filtros de escala o
        # expresiones puedan no resolver ningún símbolo, y el color cae al
        # negro por defecto más abajo.
        if self.map_settings is not None:
            ctx = QgsRenderContext.fromMapSettings(self.map_settings)
        else:
            ctx = QgsRenderContext()
            try:
                ctx.setExtent(qgis_layer.extent())
            except Exception:
                pass
        if renderer:
            renderer.startRender(ctx, qgis_layer.fields())

        label_settings = _get_label_settings(qgis_layer)

        skipped = 0
        debug_done = False
        for idx, feat in enumerate(features):
            if total > 0:
                self.progress_cb(int(idx / total * 100), f'Procesando {qgis_layer.name()}…')

            try:
                geom = feat.geometry()
                if clip_geom is not None and geom is not None and not geom.isEmpty():
                    try:
                        geom = geom.intersection(clip_geom)
                    except Exception:
                        pass
                    if geom is None or geom.isEmpty():
                        continue

                # ── Nombre de la capa DXF ────────────────────────────────
                if category_field and category_field in [f.name() for f in qgis_layer.fields()]:
                    cat_val = feat[category_field]
                    dxf_layer_name = str(cat_val) if cat_val is not None else qgis_layer.name()
                else:
                    dxf_layer_name = qgis_layer.name()

                # ── Simbología ───────────────────────────────────────────
                try:
                    symbol = renderer.symbolForFeature(feat, ctx) if renderer else None
                    symbol_error = None
                except Exception as e:
                    symbol = None
                    symbol_error = f'{type(e).__name__}: {e}'

                used_rule_fallback = False
                if symbol is None and renderer is not None:
                    try:
                        symbol = _rule_based_symbol_for_feature(renderer, feat, ctx)
                        used_rule_fallback = symbol is not None
                    except Exception as e:
                        if symbol_error is None:
                            symbol_error = f'(fallback reglas) {type(e).__name__}: {e}'

                props = _symbol_props(symbol)

                fell_back_to_black = props['color'] is None
                if fell_back_to_black:
                    from qgis.PyQt.QtGui import QColor
                    props['color'] = QColor(0, 0, 0)

                # Diagnóstico (una sola vez por capa QGIS, en la consola de
                # Python de QGIS): ayuda a identificar exactamente por qué
                # una capa concreta no está devolviendo color, sin tener
                # que adivinarlo a ciegas.
                if not debug_done:
                    debug_done = True
                    sl_types = [type(symbol.symbolLayer(i)).__name__
                                for i in range(symbol.symbolLayerCount())] if symbol else []
                    print(
                        f'[CartoDXF debug] capa="{qgis_layer.name()}" '
                        f'renderer={type(renderer).__name__ if renderer else None} '
                        f'symbol={type(symbol).__name__ if symbol else None} '
                        f'symbol_layers={sl_types} '
                        f'symbol_error={symbol_error} '
                        f'fallback_reglas={used_rule_fallback} '
                        f'color={props.get("color").name() if props.get("color") else None} '
                        f'fill_color={props.get("fill_color").name() if props.get("fill_color") else None} '
                        f'fallback_negro={fell_back_to_black}'
                    )
                    if fell_back_to_black:
                        self.progress_cb(
                            int(idx / total * 100) if total else 0,
                            f'{qgis_layer.name()}: sin color detectado, usando negro '
                            f'(ver consola de Python para más detalle).'
                        )

                # Color "principal" de esta feature para la capa DXF y las
                # etiquetas: el de relleno si existe y se ha pedido unificar
                # (ver outline_uses_fill_color), si no el de borde/línea/punto.
                if outline_uses_fill_color and props.get('fill_color') is not None:
                    main_color = props['fill_color']
                else:
                    main_color = props['color']

                lw = _lw_to_dxf(props.get('linewidth_mm', 0.25))
                ltype = props.get('linestyle', 'Continuous')

                layer_name = self._ensure_layer(dxf_layer_name, main_color, lw, ltype)

                # ── Geometría ────────────────────────────────────────────
                self._process_geometry(geom, transform, layer_name, props, qgis_layer.geometryType(),
                                       export_hatch, export_symbol_block, symbol_size,
                                       outline_uses_fill_color, hatch_pattern, hatch_scale)

                # ── Etiquetas ────────────────────────────────────────────
                if export_labels and label_field:
                    fields = [f.name() for f in qgis_layer.fields()]
                    if label_field in fields:
                        label_val = feat[label_field]
                        if label_val:
                            centroid = geom.centroid().asPoint() if geom else None
                            if centroid:
                                cp = self._pt(centroid, transform)
                                rotation = _label_rotation_for_feature(label_settings, feat, ctx, geom)
                                self._add_text(label_val, cp[0], cp[1],
                                               label_height, layer_name + '_TEXT', main_color,
                                               rotation)

            except Exception:
                # Una feature problemática (geometría inválida, valor de
                # categoría incompatible, etc.) no debe abortar todo el
                # DXF: se omite esa entidad y se continúa con las demás.
                skipped += 1
                continue

        if skipped:
            self.progress_cb(99, f'{skipped} entidad(es) omitida(s) por error en {qgis_layer.name()}.')

        if renderer:
            renderer.stopRender(ctx)

    def save(self):
        self.doc.saveas(self.output_path)
