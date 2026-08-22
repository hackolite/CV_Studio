from abc import ABCMeta, abstractmethod
import logging

logger = logging.getLogger(__name__)


class DpgNodeABC(metaclass=ABCMeta):
    _ver = '0.0.0'

    node_label = ''
    node_tag = ''

    TYPE_INT = 'Int'
    TYPE_FLOAT = 'Float'
    TYPE_IMAGE = 'Image'
    TYPE_TIME_MS = 'TimeMS'
    TYPE_JSON = 'Json'
    TYPE_SOUND = 'Sound'

    @abstractmethod
    def add_node(
        self,
        parent,
        node_id,
        pos,
        width,
        height,
        opencv_setting_dict,
    ):
        pass

    @abstractmethod
    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        pass

    @abstractmethod
    def get_setting_dict(self, node_id):
        pass

    @abstractmethod
    def set_setting_dict(self, node_id, setting_dict):
        pass

    def close(self, node_id):
        """Default cleanup: delete any file_dialog widgets stored as instance
        attributes (tag_upload_file_dialog, tag_export_file_dialog, etc.).

        File dialogs are created outside the node widget hierarchy, so
        dpg.delete_item(node_widget) does NOT remove them.  Leaving them as
        orphans causes duplicate-tag errors on undo/re-add, which is especially
        visible on Windows.

        Sub-classes should call super().close(node_id) or perform the same
        cleanup themselves.
        """
        import dearpygui.dearpygui as _dpg
        dialog_attrs = [
            'tag_upload_file_dialog',
            'tag_export_file_dialog',
            'tag_file_dialog',
        ]
        for attr in dialog_attrs:
            dialog_tag = getattr(self, attr, None)
            if dialog_tag is None:
                continue
            try:
                if _dpg.does_item_exist(dialog_tag):
                    logger.debug(
                        "DpgNodeABC.close: deleting orphan dialog tag=%s (attr=%s)",
                        dialog_tag, attr,
                    )
                    _dpg.delete_item(dialog_tag)
                    try:
                        # dialog_tag is already the alias string; remove it from
                        # the registry so undo/re-add can reuse the same tag.
                        _dpg.remove_alias(dialog_tag)
                    except Exception:
                        pass
            except Exception as exc:
                logger.warning(
                    "DpgNodeABC.close: failed to delete dialog tag=%s (attr=%s): %s",
                    dialog_tag, attr, exc,
                )
