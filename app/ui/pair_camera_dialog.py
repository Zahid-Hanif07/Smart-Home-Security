"""PySide6 dialog for pairing this desktop camera with a home."""
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.services.device_pairing_service import (
    DeviceAlreadyRegisteredError,
    DeviceCredentialProvisioningError,
    DevicePairingError,
    DevicePairingService,
    PairingResult,
)


class PairCameraDialog(QDialog):
    def __init__(self, parent=None, pairing_service: DevicePairingService | None = None):
        super().__init__(parent)
        self.setWindowTitle("Pair Camera")
        self.setModal(True)
        self.pairing_result: PairingResult | None = None
        self._pairing_service = pairing_service or DevicePairingService()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Enter the short-lived code shown in the mobile app."))

        self.code_input = QLineEdit(self)
        self.code_input.setObjectName("pairingCodeInput")
        self.code_input.setPlaceholderText("ABC-123")
        self.code_input.setMaxLength(7)
        layout.addWidget(self.code_input)

        self.status_label = QLabel(self)
        self.status_label.setObjectName("pairingStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.pair_button = QPushButton("Pair", self)
        self.pair_button.setObjectName("btnPairSubmit")
        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setObjectName("btnPairCancel")
        buttons.addWidget(self.pair_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        self.pair_button.clicked.connect(self._submit)
        self.cancel_button.clicked.connect(self.reject)
        self.code_input.returnPressed.connect(self._submit)

    def _submit(self, _checked: bool = False) -> None:
        self.pair_button.setEnabled(False)
        self.code_input.setEnabled(False)
        self.status_label.setText("Pairing…")
        try:
            result = self._pairing_service.claim(self.code_input.text())
        except DeviceCredentialProvisioningError as exc:
            self.status_label.setText(str(exc))
            self.pair_button.setEnabled(False)
            self.cancel_button.setText("Close")
            return
        except DeviceAlreadyRegisteredError as exc:
            self.status_label.setText(str(exc))
        except DevicePairingError as exc:
            self.status_label.setText(str(exc))
        else:
            self.pairing_result = result
            self.accept()
            return

        self.pair_button.setEnabled(True)
        self.code_input.setEnabled(True)
        self.code_input.setFocus()
