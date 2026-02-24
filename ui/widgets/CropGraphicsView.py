# app/ui/widgets/CropGraphicsView.py
from __future__ import annotations
from typing import List, Tuple

from PySide6.QtCore import Qt, QRect, QRectF, QPointF, Signal
from PySide6.QtGui import QPixmap, QPen, QBrush, QPainter
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsRectItem, QRubberBand, QGraphicsSimpleTextItem
)


class CropGraphicsView(QGraphicsView):
    """
    Visor con zoom (rueda), pan (botón medio) y selección de múltiples ROIs rectangulares.
    Devuelve ROIs en coordenadas de imagen (px).
    """
    # >>> NUEVO: señal para notificar cambios en los ROIs
    sig_rois_changed = Signal(list)  # list[(x,y,w,h), ...]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self._pix_item: QGraphicsPixmapItem | None = None
        self._pixmap: QPixmap | None = None

        self._rubber = QRubberBand(QRubberBand.Rectangle, self.viewport())
        self._origin = None

        self._is_panning = False
        self._pan_start = None

        # Rectángulos + etiquetas numéricas
        self._roi_items: List[QGraphicsRectItem] = []
        self._roi_labels: List[QGraphicsSimpleTextItem] = []

    # ----- Imagen -----
    def set_image(self, pix: QPixmap):
        self._scene.clear()
        self._roi_items.clear()
        self._roi_labels.clear()
        self._pix_item = self._scene.addPixmap(pix)
        self._pix_item.setZValue(0)
        self._pixmap = pix
        self.fitInView(self._pix_item, Qt.KeepAspectRatio)

    # ----- Utilidades internas -----
    def _rebuild_labels(self):
        """Crea/renumera las etiquetas '1', '2', ... sobre cada ROI."""
        # Borra etiquetas anteriores
        for lab in self._roi_labels:
            self._scene.removeItem(lab)
        self._roi_labels = []

        # Crea etiquetas nuevas
        for idx, rect_item in enumerate(self._roi_items, start=1):
            r = rect_item.rect()
            label = QGraphicsSimpleTextItem(str(idx))
            label.setBrush(QBrush(Qt.red))
            label.setZValue(2)

            # <<< NUEVO: hacer el número grande y legible
            font = label.font()
            font.setPointSize(36)   # puedes subir/bajar este valor
            label.setFont(font)
            font.setBold(True) 

            # Un poquito dentro del rectángulo, esquina superior izquierda
            label.setPos(r.x() + 2, r.y() + 2)
            self._scene.addItem(label)
            self._roi_labels.append(label)


    def _emit_rois_changed(self):
        self.sig_rois_changed.emit(self.rois())

    # ----- Zoom/Pan -----
    def wheelEvent(self, ev):
        factor = 1.15 if ev.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = ev.pos()
            self.setCursor(Qt.ClosedHandCursor)
            ev.accept()
            return
        if ev.button() == Qt.LeftButton:
            self._origin = ev.pos()
            self._rubber.setGeometry(QRect(self._origin, self._origin))
            self._rubber.show()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._is_panning and self._pan_start is not None:
            delta = ev.pos() - self._pan_start
            self._pan_start = ev.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            ev.accept()
            return
        if self._origin is not None:
            rect = QRect(self._origin, ev.pos()).normalized()
            self._rubber.setGeometry(rect)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
            ev.accept()
            return
        if ev.button() == Qt.LeftButton and self._origin is not None:
            self._rubber.hide()
            rect_view = QRect(self._origin, ev.pos()).normalized()
            self._origin = None
            if rect_view.width() > 8 and rect_view.height() > 8 and self._pix_item is not None:
                # Viewport->Scene->Image coords
                p1: QPointF = self.mapToScene(rect_view.topLeft())
                p2: QPointF = self.mapToScene(rect_view.bottomRight())
                r = QRectF(p1, p2).normalized()
                # Limitar al tamaño del pixmap
                iw = self._pix_item.pixmap().width()
                ih = self._pix_item.pixmap().height()
                r = r.intersected(QRectF(0, 0, iw, ih))
                if r.width() >= 8 and r.height() >= 8:
                    item = QGraphicsRectItem(r)
                    item.setPen(QPen(Qt.red, 2))
                    item.setBrush(QBrush(Qt.transparent))
                    item.setZValue(1)
                    self._scene.addItem(item)
                    self._roi_items.append(item)
                    self._rebuild_labels()
                    self._emit_rois_changed()
        super().mouseReleaseEvent(ev)

    # ----- Gestión de ROIs -----
    def clear_rois(self):
        for it in self._roi_items:
            self._scene.removeItem(it)
        self._roi_items.clear()
        self._rebuild_labels()   # borra las etiquetas también
        self._emit_rois_changed()

    def remove_last_roi(self):
        if self._roi_items:
            it = self._roi_items.pop(-1)
            self._scene.removeItem(it)
            self._rebuild_labels()
            self._emit_rois_changed()

    def rois(self) -> List[Tuple[int, int, int, int]]:
        """Devuelve [(x,y,w,h), ...] en px de imagen."""
        out: List[Tuple[int, int, int, int]] = []
        for it in self._roi_items:
            r = it.rect()  # QRectF en coords de imagen
            out.append((int(r.x()), int(r.y()), int(r.width()), int(r.height())))
        return out

    # >>> NUEVO: para restaurar ROIs ya guardados al cambiar de imagen
    def set_rois(self, rois: List[Tuple[int, int, int, int]]):
        """Reemplaza los ROIs actuales por los dados (x,y,w,h)."""
        # Quitar rectángulos actuales
        for it in self._roi_items:
            self._scene.removeItem(it)
        self._roi_items.clear()
        # Quitar etiquetas actuales
        for lab in self._roi_labels:
            self._scene.removeItem(lab)
        self._roi_labels.clear()

        # Crear los nuevos
        for (x, y, w, h) in rois:
            r = QRectF(float(x), float(y), float(w), float(h))
            item = QGraphicsRectItem(r)
            item.setPen(QPen(Qt.red, 2))
            item.setBrush(QBrush(Qt.transparent))
            item.setZValue(1)
            self._scene.addItem(item)
            self._roi_items.append(item)

        self._rebuild_labels()
        self._emit_rois_changed()