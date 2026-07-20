# -*- coding: utf-8 -*-
"""
cartodxf_dialog.py  —  Diálogo principal del plugin CartoDXF
"""
import traceback

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QGroupBox, QComboBox, QCheckBox,
    QDoubleSpinBox, QProgressBar, QMessageBox, QLineEdit,
    QAbstractItemView, QWidget, QLayout,
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal, QUrl, QSettings
from qgis.PyQt.QtGui import QDesktopServices

from qgis.core import QgsProject, QgsMapLayerType


# ─────────────────────────────────────────────────────────────────────────────
#  Tema claro / oscuro (mismo sistema que ProfileMaster, para mantener una
#  identidad visual unificada entre los plugins de este autor)
# ─────────────────────────────────────────────────────────────────────────────

_THEMES = {
    'dark': dict(
        bg='#22232e', panel='#2b2d3a', border='#454860', fg='#e8e9f0',
        fg_disabled='#6b6e80',
        field_bg='#1b1c25', field_fg='#f0f1f6',
        field_bg_disabled='#262833', field_fg_disabled='#6b6e80',
        tab_bg='#262834', accent='#2471A3', muted='#a4a7bd', warn='#ff7a6b',
        button_bg='#343750', button_bg_hover='#3d4060', theme_btn_bg='#343750',
        check_border='#8489a8', header_bg='#262834',
    ),
    'light': dict(
        bg='#f4f4f8', panel='#ffffff', border='#c7c9d6', fg='#1c1d27',
        fg_disabled='#9a9cab',
        field_bg='#ffffff', field_fg='#1c1d27',
        field_bg_disabled='#ececf2', field_fg_disabled='#9a9cab',
        tab_bg='#e7e8ef', accent='#1A5276', muted='#5b5d6c', warn='#c0392b',
        button_bg='#e9e9f0', button_bg_hover='#dadce6', theme_btn_bg='#e9e9f0',
        check_border='#6b6e80', header_bg='#e7e8ef',
    ),
}

_QSS_TEMPLATE = """
QWidget {{
    background: {bg};
    color: {fg};
    font-size: 9pt;
}}
QDialog {{ background: {bg}; }}
QGroupBox {{
    font-weight: bold;
    border: 1px solid {border};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 6px;
    background: {panel};
    color: {fg};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: {fg};
}}
QGroupBox:disabled {{ color: {fg_disabled}; }}
QLabel {{ background: transparent; color: {fg}; }}
QCheckBox {{ background: transparent; color: {fg}; spacing: 6px; }}
QCheckBox:disabled {{ color: {fg_disabled}; }}
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1.5px solid {check_border};
    border-radius: 3px;
    background: {field_bg};
}}
QCheckBox::indicator:hover {{
    border: 1.5px solid {accent};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border: 1.5px solid {accent};
}}
QCheckBox::indicator:checked:hover {{
    background: {accent};
    border: 1.5px solid {check_border};
}}
QCheckBox::indicator:disabled {{
    background: {field_bg_disabled};
    border: 1.5px solid {border};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    padding: 2px 4px;
    border: 1px solid {border};
    border-radius: 3px;
    background: {field_bg};
    color: {field_fg};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background: {field_bg_disabled};
    color: {field_fg_disabled};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {fg};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {field_bg};
    color: {field_fg};
    border: 1px solid {border};
    selection-background-color: {accent};
    selection-color: white;
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 16px;
    border-left: 1px solid {border};
    border-bottom: 1px solid {border};
    border-top-right-radius: 3px;
    background: {button_bg};
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 16px;
    border-left: 1px solid {border};
    border-top: 1px solid {border};
    border-bottom-right-radius: 3px;
    background: {button_bg};
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background: {button_bg_hover};
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {fg};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {fg};
}}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
    border-bottom-color: {fg_disabled};
    border-top-color: {fg_disabled};
}}
QPushButton {{
    background: {button_bg};
    color: {fg};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{ background: {button_bg_hover}; }}
QPushButton:disabled {{ background: {border}; color: {fg_disabled}; }}
QPushButton#btn_run {{
    background: #1A5276;
    color: white;
    font-weight: bold;
    padding: 8px 22px;
    border-radius: 5px;
    font-size: 10pt;
    border: none;
}}
QPushButton#btn_run:hover {{ background: #2471A3; }}
QPushButton#btn_run:disabled {{ background: {border}; color: {fg_disabled}; }}
QPushButton#btn_donate {{
    background: #E67E22;
    color: white;
    font-weight: bold;
    padding: 8px 14px;
    border-radius: 5px;
    font-size: 9pt;
    border: none;
}}
QPushButton#btn_donate:hover {{ background: #CA6F1E; }}
QPushButton#btn_close {{
    padding: 8px 16px;
    border-radius: 5px;
    font-size: 10pt;
}}
QPushButton#btn_theme {{
    padding: 5px 12px;
    border-radius: 14px;
    font-size: 9pt;
    background: {theme_btn_bg};
    border: 1px solid {border};
    color: {fg};
}}
QPushButton#btn_theme:hover {{ background: {button_bg_hover}; }}
QProgressBar {{
    border: 1px solid {border};
    border-radius: 4px;
    text-align: center;
    height: 18px;
    background: {field_bg};
    color: {fg};
}}
QProgressBar::chunk {{ background: #2471A3; border-radius: 3px; }}
QLabel#lbl_title {{
    font-size: 13pt;
    font-weight: bold;
    padding: 4px 0;
    color: {fg};
}}
QLabel#lbl_info {{
    font-size: 8pt;
    color: {muted};
}}
QLabel#lbl_header {{
    font-size: 8pt;
    font-weight: bold;
    color: {muted};
    background: {header_bg};
    padding: 4px;
}}
QListWidget {{
    background: {panel};
    border: 1px solid {border};
    border-radius: 3px;
}}
QListWidget::item {{
    border-bottom: 1px solid {border};
}}
"""


def _build_stylesheet(theme):
    colors = _THEMES.get(theme, _THEMES['dark'])
    return _QSS_TEMPLATE.format(**colors)


# ─────────────────────────────────────────────────────────────────────────────
#  Idioma de la interfaz (ES / EN). Textos visibles del diálogo.
#  Los tooltips más largos y detallados se mantienen en español para no
#  disparar el alcance del plugin; los rótulos, botones, cabeceras y mensajes
#  que el usuario ve a simple vista sí están en ambos idiomas.
# ─────────────────────────────────────────────────────────────────────────────

_STRINGS = {
    'es': dict(
        title='🗂️  CartoDXF',
        subtitle='Exporta capas de QGIS a DXF, una capa DXF por categoría',
        grp_layers='Capas a exportar',
        btn_all='Seleccionar todas',
        btn_none='Deseleccionar todas',
        col_header='  ☑  Capa                                    Capa DXF                       Texto/etiqueta',
        col_dxf='Capa DXF:',
        col_label='Texto/etiqueta:',
        combo_layer_name='(nombre de capa)',
        combo_no_label='(sin etiqueta)',
        chk_include_tooltip='Incluir o excluir esta capa de la exportación.',
        grp_opts='Opciones',
        chk_labels='Exportar etiquetas como texto DXF',
        chk_hatch='Exportar relleno de polígonos (hatch)',
        chk_hatch_tooltip='Activo: exporta relleno en áreas (sólido o con patrón).\n'
        'Inactivo: exporta solo los contornos cerrados.',
        lbl_hatch_pattern='Patrón de relleno:',
        hatch_patterns=(
            ('Sólido', 'SOLID'),
            ('Líneas diagonales', 'ANSI31'),
            ('Líneas horizontales', 'LINE'),
            ('Rejilla / cruzado', 'NET'),
            ('Puntos', 'DOTS'),
        ),
        lbl_hatch_scale='Escala del patrón:',
        chk_outline_fill='Usar el color de relleno también en el contorno de los polígonos',
        chk_symbol_block='Exportar también el símbolo de QGIS como bloque DXF (en puntos)',
        lbl_symbol_size='Tamaño del bloque (unid. del mapa):',
        lbl_text_height='Altura texto (m):',
        chk_reproject='Reproyectar al CRS del proyecto',
        chk_extent_only='Exportar solo entidades dentro de la vista actual del lienzo',
        chk_extent_only_tooltip='Activa esto para exportar solo lo que ves en el mapa\n'
        'ahora mismo (útil si una capa no tiene un filtro propio aplicado\n'
        'y por eso se exporta entera, p.ej. toda la provincia en vez de\n'
        'un solo municipio). Se combina con cualquier filtro que ya tenga\n'
        'la capa: solo se exportan las entidades que cumplen AMBAS cosas.',
        grp_output='Archivo de salida',
        placeholder_output='Selecciona la ruta del archivo DXF…',
        btn_export='▶  Exportar DXF',
        btn_donate='☕  Invítame a un café',
        btn_donate_tooltip='Si este plugin te resulta útil, apoya su desarrollo.',
        btn_close='Cerrar',
        status_ready='Listo.',
        btn_lang='EN',
        btn_lang_tooltip='Switch interface to English',
        warn_title='Aviso',
        warn_no_output='Selecciona un archivo de salida.',
        warn_no_layers='Selecciona al menos una capa.',
        save_dialog_title='Guardar DXF',
        done_title='Exportación completada',
        done_msg='Archivo DXF generado correctamente:\n{path}',
        status_done='✅ Exportado: {path}',
        status_error='❌ Error en la exportación',
        error_title='Error',
    ),
    'en': dict(
        title='🗂️  CartoDXF',
        subtitle='Export QGIS layers to DXF, one DXF layer per category',
        grp_layers='Layers to export',
        btn_all='Select all',
        btn_none='Deselect all',
        col_header='  ☑  Layer                                    DXF layer                       Text/label',
        col_dxf='DXF layer:',
        col_label='Text/label:',
        combo_layer_name='(layer name)',
        combo_no_label='(no label)',
        chk_include_tooltip='Include or exclude this layer from the export.',
        grp_opts='Options',
        chk_labels='Export labels as DXF text',
        chk_hatch='Export polygon fill (hatch)',
        chk_hatch_tooltip='Enabled: exports area fill (solid or pattern).\n'
        'Disabled: exports only the closed outlines.',
        lbl_hatch_pattern='Fill pattern:',
        hatch_patterns=(
            ('Solid', 'SOLID'),
            ('Diagonal lines', 'ANSI31'),
            ('Horizontal lines', 'LINE'),
            ('Grid / cross-hatch', 'NET'),
            ('Dots', 'DOTS'),
        ),
        lbl_hatch_scale='Pattern scale:',
        chk_outline_fill='Also use the fill color for the polygon outline',
        chk_symbol_block='Also export the QGIS symbol as a DXF block (points)',
        lbl_symbol_size='Block size (map units):',
        lbl_text_height='Text height (m):',
        chk_reproject='Reproject to the project CRS',
        chk_extent_only='Export only features within the current canvas view',
        chk_extent_only_tooltip='Enable this to export only what you currently see on\n'
        'the map (useful when a layer has no filter of its own applied\n'
        'and therefore gets exported in full, e.g. the whole province\n'
        'instead of a single municipality). It combines with any filter\n'
        'the layer already has: only features matching BOTH are exported.',
        grp_output='Output file',
        placeholder_output='Choose the DXF output path…',
        btn_export='▶  Export DXF',
        btn_donate='☕  Buy me a coffee',
        btn_donate_tooltip='If this plugin is useful to you, support its development.',
        btn_close='Close',
        status_ready='Ready.',
        btn_lang='ES',
        btn_lang_tooltip='Cambiar la interfaz a español',
        warn_title='Notice',
        warn_no_output='Choose an output file.',
        warn_no_layers='Select at least one layer.',
        save_dialog_title='Save DXF',
        done_title='Export completed',
        done_msg='DXF file generated successfully:\n{path}',
        status_done='✅ Exported: {path}',
        status_error='❌ Export error',
        error_title='Error',
    ),
}


class ExportWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        try:
            from .dxf_exporter import DXFExporter

            p = self.params
            exporter = DXFExporter(
                output_path=p['output_path'],
                target_crs=p.get('target_crs'),
                progress_cb=lambda v, msg: self.progress.emit(v, msg),
                map_settings=p.get('map_settings'),
                extent=p.get('extent'),
                extent_crs=p.get('extent_crs'),
            )

            layers = p['layers']
            for i, item in enumerate(layers):
                self.progress.emit(
                    int(i / len(layers) * 95),
                    f"Exportando capa {i + 1}/{len(layers)}: {item['layer'].name()}"
                )
                exporter.add_layer(
                    qgis_layer=item['layer'],
                    category_field=item.get('category_field'),
                    label_field=item.get('label_field'),
                    label_height=p.get('label_height', 2.0),
                    export_labels=p.get('export_labels', True),
                    export_hatch=p.get('export_hatch', True),
                    export_symbol_block=p.get('export_symbol_block', False),
                    symbol_size=p.get('symbol_size', 1.0),
                    outline_uses_fill_color=p.get('outline_uses_fill_color', True),
                    hatch_pattern=p.get('hatch_pattern', 'SOLID'),
                    hatch_scale=p.get('hatch_scale', 1.0),
                )

            self.progress.emit(97, 'Guardando archivo DXF…')
            exporter.save()
            self.progress.emit(100, 'Exportación completada.')
            self.finished.emit(p['output_path'])

        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")


class LayerConfigWidget(QWidget):
    """Widget de configuración por capa."""

    def __init__(self, layer, strings, parent=None):
        super().__init__(parent)
        self.layer = layer
        self._strings = strings
        self._build_ui()
        self.chk_include.toggled.connect(self._on_toggle_include)
        self._on_toggle_include(self.chk_include.isChecked())

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        # Checkbox individual: decide si esta capa se exporta o no.
        # (Va DENTRO del widget de la fila -a diferencia del checkbox nativo
        # de QListWidgetItem- porque este widget cubre toda la fila y, si no,
        # el clic nunca llegaría al indicador nativo: por eso antes solo
        # funcionaban "Seleccionar todas"/"Deseleccionar todas".)
        self.chk_include = QCheckBox()
        self.chk_include.setChecked(True)
        self.chk_include.setToolTip(self._strings['chk_include_tooltip'])
        layout.addWidget(self.chk_include)

        # Nombre de la capa
        self.lbl_name = QLabel(self.layer.name())
        self.lbl_name.setMinimumWidth(90)
        self.lbl_name.setMaximumWidth(180)
        self.lbl_name.setToolTip(self.layer.source())
        layout.addWidget(self.lbl_name)

        # Campo de categoría → define el NOMBRE DE LA CAPA DXF resultante.
        self.lbl_cat = QLabel(self._strings['col_dxf'])
        layout.addWidget(self.lbl_cat)
        self.combo_cat = QComboBox()
        self.combo_cat.setMinimumWidth(120)
        self.combo_cat.setToolTip(
            'Determina el nombre de la capa DXF que se creará.\n'
            '"(nombre de capa)" usa el nombre de esta capa de QGIS tal cual.\n'
            'Si eliges un campo, cada valor distinto de ese campo genera\n'
            'su propia capa DXF (p.ej. una capa por cada tipo de vía).'
        )
        self.combo_cat.addItem(self._strings['combo_layer_name'], None)
        for field in self.layer.fields():
            self.combo_cat.addItem(field.name(), field.name())
        # Autodetectar campo "layer" o "LAYER"
        for i in range(self.combo_cat.count()):
            if self.combo_cat.itemText(i).lower() == 'layer':
                self.combo_cat.setCurrentIndex(i)
                break
        layout.addWidget(self.combo_cat)

        # Campo de etiqueta → texto DXF que se escribe junto a cada entidad.
        self.lbl_lbl = QLabel(self._strings['col_label'])
        layout.addWidget(self.lbl_lbl)
        self.combo_lbl = QComboBox()
        self.combo_lbl.setMinimumWidth(120)
        self.combo_lbl.setToolTip(
            'Campo cuyo valor se escribe como texto (entidad TEXT) en el\n'
            'DXF, junto al centroide de cada elemento. Es independiente\n'
            'de "Capa DXF": puedes usar el mismo campo en ambos, campos\n'
            'distintos, o dejar esta opción en "(sin etiqueta)" si solo\n'
            'quieres organizar capas sin escribir ningún rótulo.'
        )
        self.combo_lbl.addItem(self._strings['combo_no_label'], None)
        for field in self.layer.fields():
            self.combo_lbl.addItem(field.name(), field.name())
        # Autodetectar campo de etiqueta activo en QGIS
        if self.layer.labelsEnabled():
            lbl_field = self.layer.labeling().settings().fieldName if self.layer.labeling() else ''
            for i in range(self.combo_lbl.count()):
                if self.combo_lbl.itemText(i) == lbl_field:
                    self.combo_lbl.setCurrentIndex(i)
                    break
        layout.addWidget(self.combo_lbl)
        layout.addStretch()

    def category_field(self):
        return self.combo_cat.currentData()

    def label_field(self):
        return self.combo_lbl.currentData()

    def is_included(self):
        return self.chk_include.isChecked()

    def set_included(self, checked):
        self.chk_include.setChecked(checked)

    def _on_toggle_include(self, checked):
        # Si la capa está desmarcada, se deshabilitan sus combos para dejar
        # visualmente claro que no participarán en la exportación.
        self.lbl_name.setEnabled(checked)
        self.lbl_cat.setEnabled(checked)
        self.combo_cat.setEnabled(checked)
        self.lbl_lbl.setEnabled(checked)
        self.combo_lbl.setEnabled(checked)

    def retranslate(self, strings):
        self._strings = strings
        self.chk_include.setToolTip(strings['chk_include_tooltip'])
        self.lbl_cat.setText(strings['col_dxf'])
        self.lbl_lbl.setText(strings['col_label'])
        self.combo_cat.setItemText(0, strings['combo_layer_name'])
        self.combo_lbl.setItemText(0, strings['combo_no_label'])


class CartoDXFDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.worker = None
        self.layer_widgets = {}  # layer_id → LayerConfigWidget

        self._settings = QSettings()
        saved_theme = self._settings.value("CartoDXF/theme", None)
        if saved_theme in ('dark', 'light'):
            self._theme = saved_theme
        else:
            bg_lightness = self.palette().window().color().lightness()
            self._theme = 'dark' if bg_lightness < 128 else 'light'

        saved_lang = self._settings.value("CartoDXF/lang", None)
        if saved_lang in ('es', 'en'):
            self._lang = saved_lang
        else:
            # Detecta el idioma del sistema/QGIS; si no es español, se
            # arranca en inglés por defecto.
            sys_lang = QSettings().value("locale/userLocale", "") or ""
            self._lang = 'es' if str(sys_lang).lower().startswith('es') else 'en'
        self.strings = _STRINGS[self._lang]

        self.setWindowTitle('CartoDXF')
        self._build_ui()
        self._load_layers()

        # El tamaño mínimo se calcula a partir de lo que el propio contenido
        # necesita (en vez de un valor fijo tipo 780x600, que se quedaba
        # corto en altura cada vez que se añadían opciones nuevas y permitía
        # encoger la ventana hasta que los textos y controles se solapaban).
        # Con SetMinimumSize, Qt mantiene el mínimo de la ventana sincronizado
        # con el mínimo real del layout tanto en ancho como en alto, así que
        # ya no hace falta recalcularlo a mano si se agregan más opciones.
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.resize(820, 760)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(8)
        main.setContentsMargins(12, 12, 12, 12)

        self.setStyleSheet(_build_stylesheet(self._theme))

        s = self.strings

        # ── Cabecera ──────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        self.lbl_title = QLabel(s['title'])
        self.lbl_title.setObjectName('lbl_title')
        header_row.addWidget(self.lbl_title)
        header_row.addStretch()

        self.btn_lang = QPushButton()
        self.btn_lang.setObjectName('btn_theme')
        self.btn_lang.clicked.connect(self._toggle_lang)
        header_row.addWidget(self.btn_lang)

        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName('btn_theme')
        self.btn_theme.clicked.connect(self._toggle_theme)
        header_row.addWidget(self.btn_theme)
        main.addLayout(header_row)

        self.lbl_subtitle = QLabel(s['subtitle'])
        self.lbl_subtitle.setObjectName('lbl_info')
        main.addWidget(self.lbl_subtitle)

        # ── Grupo de capas ────────────────────────────────────────────────
        self.grp_layers = QGroupBox(s['grp_layers'])
        grp_layout = QVBoxLayout(self.grp_layers)

        # Botones selección
        sel_row = QHBoxLayout()
        self.btn_all = QPushButton(s['btn_all'])
        self.btn_all.clicked.connect(self._select_all)
        self.btn_none = QPushButton(s['btn_none'])
        self.btn_none.clicked.connect(self._select_none)
        sel_row.addWidget(self.btn_all)
        sel_row.addWidget(self.btn_none)
        sel_row.addStretch()
        grp_layout.addLayout(sel_row)

        # Cabecera
        self.lbl_col_header = QLabel(s['col_header'])
        self.lbl_col_header.setObjectName('lbl_header')
        grp_layout.addWidget(self.lbl_col_header)

        # Lista de capas
        self.list_layers = QListWidget()
        self.list_layers.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list_layers.setMinimumHeight(220)
        grp_layout.addWidget(self.list_layers)

        main.addWidget(self.grp_layers)

        # ── Opciones generales ────────────────────────────────────────────
        self.grp_opts = QGroupBox(s['grp_opts'])
        opts_grid = QGridLayout(self.grp_opts)
        opts_grid.setSpacing(6)

        self.chk_labels = QCheckBox(s['chk_labels'])
        self.chk_labels.setChecked(True)
        opts_grid.addWidget(self.chk_labels, 0, 0, 1, 2)

        self.chk_hatch = QCheckBox(s['chk_hatch'])
        self.chk_hatch.setChecked(True)
        self.chk_hatch.setToolTip(s['chk_hatch_tooltip'])
        self.chk_hatch.toggled.connect(self._toggle_hatch_options)
        opts_grid.addWidget(self.chk_hatch, 1, 0, 1, 2)

        self.lbl_hatch_pattern = QLabel(s['lbl_hatch_pattern'])
        opts_grid.addWidget(self.lbl_hatch_pattern, 2, 0)
        self.combo_hatch_pattern = QComboBox()
        for label, value in s['hatch_patterns']:
            self.combo_hatch_pattern.addItem(label, value)
        self.combo_hatch_pattern.currentIndexChanged.connect(self._toggle_hatch_scale)
        opts_grid.addWidget(self.combo_hatch_pattern, 2, 1)

        self.lbl_hatch_scale = QLabel(s['lbl_hatch_scale'])
        opts_grid.addWidget(self.lbl_hatch_scale, 3, 0)
        self.spin_hatch_scale = QDoubleSpinBox()
        self.spin_hatch_scale.setRange(0.01, 1000.0)
        self.spin_hatch_scale.setDecimals(2)
        self.spin_hatch_scale.setValue(1.0)
        self.spin_hatch_scale.setSingleStep(0.5)
        opts_grid.addWidget(self.spin_hatch_scale, 3, 1)
        self._toggle_hatch_scale()

        self.chk_outline_fill = QCheckBox(s['chk_outline_fill'])
        self.chk_outline_fill.setChecked(True)
        self.chk_outline_fill.setToolTip(
            'En un renderer "Categorizado" con colores aleatorios, normalmente\n'
            'solo varía el RELLENO; el borde se queda en el gris por defecto\n'
            'de QGIS, igual en todas las categorías. En AutoCAD ese borde es\n'
            'lo que más se ve, así que esta opción (activa por defecto) hace\n'
            'que el contorno tome el mismo color que el relleno de su categoría.\n'
            'Desactívala si tu estilo usa un color de borde distinto a propósito.'
        )
        opts_grid.addWidget(self.chk_outline_fill, 4, 0, 1, 2)

        self.chk_symbol_block = QCheckBox(s['chk_symbol_block'])
        self.chk_symbol_block.setChecked(False)
        self.chk_symbol_block.setToolTip(
            'Además del punto (entidad POINT), inserta un bloque (INSERT) con\n'
            'una aproximación del símbolo de QGIS: círculo, cuadrado, triángulo,\n'
            'diamante, cruz, X, estrella, pentágono o hexágono según la forma\n'
            'configurada en "Marcador simple". Si el símbolo es un icono SVG o\n'
            'una imagen, se usa un círculo como aproximación genérica, ya que\n'
            'no es posible convertir un icono arbitrario a geometría DXF.'
        )
        self.chk_symbol_block.toggled.connect(self._toggle_symbol_size)
        opts_grid.addWidget(self.chk_symbol_block, 5, 0, 1, 2)

        self.lbl_symbol_size = QLabel(s['lbl_symbol_size'])
        self.lbl_symbol_size.setEnabled(False)
        opts_grid.addWidget(self.lbl_symbol_size, 6, 0)
        self.spin_symbol_size = QDoubleSpinBox()
        self.spin_symbol_size.setRange(0.001, 100000.0)
        self.spin_symbol_size.setDecimals(3)
        self.spin_symbol_size.setValue(1.0)
        self.spin_symbol_size.setSingleStep(0.1)
        self.spin_symbol_size.setEnabled(False)
        self.spin_symbol_size.setToolTip(
            'El tamaño del símbolo en QGIS está en mm/px de pantalla y no\n'
            'corresponde a ninguna medida real sobre el terreno, así que aquí\n'
            'se indica directamente el tamaño (diámetro) que debe tener el\n'
            'bloque en las unidades del mapa (p.ej. metros).'
        )
        opts_grid.addWidget(self.spin_symbol_size, 6, 1)

        self.lbl_text_height = QLabel(s['lbl_text_height'])
        opts_grid.addWidget(self.lbl_text_height, 7, 0)
        self.spin_lbl_h = QDoubleSpinBox()
        self.spin_lbl_h.setRange(0.1, 100.0)
        self.spin_lbl_h.setValue(2.0)
        self.spin_lbl_h.setSingleStep(0.5)
        opts_grid.addWidget(self.spin_lbl_h, 7, 1)

        self.chk_reproject = QCheckBox(s['chk_reproject'])
        self.chk_reproject.setChecked(True)
        opts_grid.addWidget(self.chk_reproject, 8, 0, 1, 2)

        self.chk_extent_only = QCheckBox(s['chk_extent_only'])
        self.chk_extent_only.setChecked(False)
        self.chk_extent_only.setToolTip(s['chk_extent_only_tooltip'])
        opts_grid.addWidget(self.chk_extent_only, 9, 0, 1, 2)

        main.addWidget(self.grp_opts)

        # ── Archivo de salida ─────────────────────────────────────────────
        self.grp_out = QGroupBox(s['grp_output'])
        out_row = QHBoxLayout(self.grp_out)
        self.edit_output = QLineEdit()
        self.edit_output.setPlaceholderText(s['placeholder_output'])
        btn_browse = QPushButton('…')
        btn_browse.setMaximumWidth(32)
        btn_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self.edit_output)
        out_row.addWidget(btn_browse)
        main.addWidget(self.grp_out)

        # ── Progreso ──────────────────────────────────────────────────────
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        main.addWidget(self.progress)

        self.lbl_status = QLabel(s['status_ready'])
        self.lbl_status.setObjectName('lbl_info')
        main.addWidget(self.lbl_status)

        # ── Botones ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self.btn_export = QPushButton(s['btn_export'])
        self.btn_export.setObjectName('btn_run')
        self.btn_export.clicked.connect(self._run_export)
        btn_row.addWidget(self.btn_export)

        btn_row.addStretch()

        self.btn_donate = QPushButton(s['btn_donate'])
        self.btn_donate.setObjectName('btn_donate')
        self.btn_donate.setToolTip(s['btn_donate_tooltip'])
        self.btn_donate.clicked.connect(self._open_donate)
        btn_row.addWidget(self.btn_donate)

        self.btn_close = QPushButton(s['btn_close'])
        self.btn_close.setObjectName('btn_close')
        self.btn_close.clicked.connect(self.close)
        btn_row.addWidget(self.btn_close)

        main.addLayout(btn_row)

        self._update_theme_button()
        self._update_lang_button()

    # ── Tema ──────────────────────────────────────────────────────────────────

    def _toggle_theme(self):
        self._theme = 'light' if self._theme == 'dark' else 'dark'
        self.setStyleSheet(_build_stylesheet(self._theme))
        self._settings.setValue("CartoDXF/theme", self._theme)
        self._update_theme_button()

    def _update_theme_button(self):
        if self._theme == 'dark':
            if self._lang == 'es':
                self.btn_theme.setText("☀️  Modo claro")
                self.btn_theme.setToolTip("Cambiar a modo claro (fondos claros, textos oscuros)")
            else:
                self.btn_theme.setText("☀️  Light mode")
                self.btn_theme.setToolTip("Switch to light mode (light background, dark text)")
        else:
            if self._lang == 'es':
                self.btn_theme.setText("🌙  Modo oscuro")
                self.btn_theme.setToolTip("Cambiar a modo oscuro (fondos oscuros, textos claros)")
            else:
                self.btn_theme.setText("🌙  Dark mode")
                self.btn_theme.setToolTip("Switch to dark mode (dark background, light text)")

    # ── Idioma ────────────────────────────────────────────────────────────────

    def _toggle_lang(self):
        self._lang = 'en' if self._lang == 'es' else 'es'
        self._settings.setValue("CartoDXF/lang", self._lang)
        self.strings = _STRINGS[self._lang]
        self._retranslate()

    def _update_lang_button(self):
        self.btn_lang.setText(f"🌐  {self.strings['btn_lang']}")
        self.btn_lang.setToolTip(self.strings['btn_lang_tooltip'])

    def _retranslate(self):
        s = self.strings
        self.lbl_title.setText(s['title'])
        self.lbl_subtitle.setText(s['subtitle'])
        self.grp_layers.setTitle(s['grp_layers'])
        self.btn_all.setText(s['btn_all'])
        self.btn_none.setText(s['btn_none'])
        self.lbl_col_header.setText(s['col_header'])
        self.grp_opts.setTitle(s['grp_opts'])
        self.chk_labels.setText(s['chk_labels'])
        self.chk_hatch.setText(s['chk_hatch'])
        self.chk_hatch.setToolTip(s['chk_hatch_tooltip'])
        self.lbl_hatch_pattern.setText(s['lbl_hatch_pattern'])
        current_pattern = self.combo_hatch_pattern.currentData()
        self.combo_hatch_pattern.blockSignals(True)
        self.combo_hatch_pattern.clear()
        for label, value in s['hatch_patterns']:
            self.combo_hatch_pattern.addItem(label, value)
        idx = self.combo_hatch_pattern.findData(current_pattern)
        self.combo_hatch_pattern.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_hatch_pattern.blockSignals(False)
        self.lbl_hatch_scale.setText(s['lbl_hatch_scale'])
        self.chk_outline_fill.setText(s['chk_outline_fill'])
        self.chk_symbol_block.setText(s['chk_symbol_block'])
        self.lbl_symbol_size.setText(s['lbl_symbol_size'])
        self.lbl_text_height.setText(s['lbl_text_height'])
        self.chk_reproject.setText(s['chk_reproject'])
        self.chk_extent_only.setText(s['chk_extent_only'])
        self.chk_extent_only.setToolTip(s['chk_extent_only_tooltip'])
        self.grp_out.setTitle(s['grp_output'])
        self.edit_output.setPlaceholderText(s['placeholder_output'])
        self.lbl_status.setText(s['status_ready'])
        self.btn_export.setText(s['btn_export'])
        self.btn_donate.setText(s['btn_donate'])
        self.btn_donate.setToolTip(s['btn_donate_tooltip'])
        self.btn_close.setText(s['btn_close'])
        self._update_theme_button()
        self._update_lang_button()
        for widget in self.layer_widgets.values():
            widget.retranslate(s)

    # ── Carga de capas ────────────────────────────────────────────────────────

    def _load_layers(self):
        self.list_layers.clear()
        self.layer_widgets.clear()

        layers = QgsProject.instance().mapLayers().values()
        vector_layers = [lyr for lyr in layers if lyr.type() == QgsMapLayerType.VectorLayer]

        for layer in vector_layers:
            item = QListWidgetItem()
            # Este item ya NO usa su propio checkbox nativo: el checkbox real
            # vive dentro de LayerConfigWidget (ver más abajo), porque el
            # widget de la fila cubre todo el ancho y bloquearía los clics
            # sobre el indicador nativo del QListWidgetItem.
            item.setData(Qt.ItemDataRole.UserRole, layer.id())

            widget = LayerConfigWidget(layer, self.strings)
            self.layer_widgets[layer.id()] = widget

            item.setSizeHint(widget.sizeHint())
            self.list_layers.addItem(item)
            self.list_layers.setItemWidget(item, widget)

    # ── Selección de capas ────────────────────────────────────────────────────

    def _select_all(self):
        for widget in self.layer_widgets.values():
            widget.set_included(True)

    def _select_none(self):
        for widget in self.layer_widgets.values():
            widget.set_included(False)

    def _toggle_symbol_size(self, checked):
        self.lbl_symbol_size.setEnabled(checked)
        self.spin_symbol_size.setEnabled(checked)

    def _toggle_hatch_options(self, checked):
        self.lbl_hatch_pattern.setEnabled(checked)
        self.combo_hatch_pattern.setEnabled(checked)
        self._toggle_hatch_scale()

    def _toggle_hatch_scale(self):
        is_solid = self.combo_hatch_pattern.currentData() in (None, 'SOLID')
        enabled = self.chk_hatch.isChecked() and not is_solid
        self.lbl_hatch_scale.setEnabled(enabled)
        self.spin_hatch_scale.setEnabled(enabled)

    # ── Archivo salida ────────────────────────────────────────────────────────

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.strings['save_dialog_title'], '', 'Archivos DXF (*.dxf)'
        )
        if path:
            if not path.lower().endswith('.dxf'):
                path += '.dxf'
            self.edit_output.setText(path)

    # ── Exportación ───────────────────────────────────────────────────────────

    def _run_export(self):
        s = self.strings
        output_path = self.edit_output.text().strip()
        if not output_path:
            QMessageBox.warning(self, s['warn_title'], s['warn_no_output'])
            return

        # Capas seleccionadas (checkbox propio de cada fila, ver LayerConfigWidget)
        selected_layers = []
        for layer_id, widget in self.layer_widgets.items():
            if widget.is_included():
                layer = QgsProject.instance().mapLayer(layer_id)
                if layer:
                    selected_layers.append({
                        'layer': layer,
                        'category_field': widget.category_field(),
                        'label_field': widget.label_field(),
                    })

        if not selected_layers:
            QMessageBox.warning(self, s['warn_title'], s['warn_no_layers'])
            return

        # CRS destino
        target_crs = None
        if self.chk_reproject.isChecked():
            target_crs = QgsProject.instance().crs()

        # Ajustes del lienzo real de QGIS: se usan SIEMPRE para construir un
        # contexto de render válido (extensión/escala), lo que hace que
        # renderers "Basado en reglas" con filtros de escala resuelvan bien
        # el símbolo en vez de caer al negro por defecto.
        map_settings = self.iface.mapCanvas().mapSettings()

        extent = None
        extent_crs = None
        if self.chk_extent_only.isChecked():
            extent = self.iface.mapCanvas().extent()
            extent_crs = map_settings.destinationCrs()

        params = {
            'output_path': output_path,
            'layers': selected_layers,
            'target_crs': target_crs,
            'map_settings': map_settings,
            'extent': extent,
            'extent_crs': extent_crs,
            'export_labels': self.chk_labels.isChecked(),
            'export_hatch': self.chk_hatch.isChecked(),
            'hatch_pattern': self.combo_hatch_pattern.currentData() or 'SOLID',
            'hatch_scale': self.spin_hatch_scale.value(),
            'outline_uses_fill_color': self.chk_outline_fill.isChecked(),
            'export_symbol_block': self.chk_symbol_block.isChecked(),
            'symbol_size': self.spin_symbol_size.value(),
            'label_height': self.spin_lbl_h.value(),
        }

        self.btn_export.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        self.worker = ExportWorker(params)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value, msg):
        self.progress.setValue(value)
        self.lbl_status.setText(msg)

    def _on_finished(self, path):
        s = self.strings
        self.btn_export.setEnabled(True)
        self.lbl_status.setText(s['status_done'].format(path=path))
        QMessageBox.information(
            self, s['done_title'], s['done_msg'].format(path=path)
        )

    def _on_error(self, msg):
        s = self.strings
        self.btn_export.setEnabled(True)
        self.progress.setVisible(False)
        self.lbl_status.setText(s['status_error'])
        QMessageBox.critical(self, s['error_title'], msg)

    # ── Donativo ──────────────────────────────────────────────────────────────

    def _open_donate(self):
        QDesktopServices.openUrl(
            QUrl('https://www.paypal.com/donate/?hosted_button_id=UF9SYUY42GWTG')
        )
