# -*- coding: utf-8 -*-
"""
cartodxf.py  —  Plugin principal CartoDXF
"""
import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .cartodxf_dialog import CartoDXFDialog


class CartoDXFPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dock = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
        self.action = QAction(icon, 'CartoDXF', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu('&CartoDXF', self.action)

    def unload(self):
        self.iface.removePluginVectorMenu('&CartoDXF', self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

    def run(self):
        # El panel ya NO es una ventana modal de usar-y-cerrar: es un
        # QDockWidget persistente, como los paneles nativos de QGIS
        # ("Capas", "Navegador"...). No bloquea el lienzo ni el resto de
        # QGIS mientras está abierto, y se puede anclar a cualquier
        # lateral arrastrándolo por su barra de título, o dejarlo
        # flotando (comportamiento por defecto, como antes).
        if self.dock is None:
            self.dock = CartoDXFDialog(self.iface)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
            self.dock.setFloating(True)
        else:
            # Reabrir desde el icono/menú refresca la tabla de capas por si
            # el proyecto ha cambiado mientras el panel estaba oculto.
            self.dock._sync_layers()

        self.dock.show()
        self.dock.raise_()
        self.dock.activateWindow()
