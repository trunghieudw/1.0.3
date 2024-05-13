import os
from typing import Callable, Optional, Sequence

import pvporcupine
import pvrhino


class PicovoiceError(Exception):
    pass


class PicovoiceMemoryError(PicovoiceError):
    pass


class PicovoiceIOError(PicovoiceError):
    pass


class PicovoiceInvalidArgumentError(PicovoiceError):
    pass


class PicovoiceStopIterationError(PicovoiceError):
    pass


class PicovoiceKeyError(PicovoiceError):
    pass


class PicovoiceInvalidStateError(PicovoiceError):
    pass


class PicovoiceRuntimeError(PicovoiceError):
    pass


class PicovoiceActivationError(PicovoiceError):
    pass


class PicovoiceActivationLimitError(PicovoiceError):
    pass


class PicovoiceActivationThrottledError(PicovoiceError):
    pass


class PicovoiceActivationRefusedError(PicovoiceError):
    pass


_PPN_RHN_ERROR_TO_PICOVOICE_ERROR = {
    pvporcupine.PorcupineError: PicovoiceError,
    pvrhino.RhinoError: PicovoiceError,
    pvporcupine.PorcupineMemoryError: PicovoiceMemoryError,
    pvrhino.RhinoMemoryError: PicovoiceMemoryError,
    pvporcupine.PorcupineIOError: PicovoiceIOError,
    pvrhino.RhinoIOError: PicovoiceIOError,
    pvporcupine.PorcupineInvalidArgumentError: PicovoiceInvalidArgumentError,
    pvrhino.RhinoInvalidArgumentError: PicovoiceInvalidArgumentError,
    pvporcupine.PorcupineStopIterationError: PicovoiceStopIterationError,
    pvrhino.RhinoStopIterationError: PicovoiceStopIterationError,
    pvporcupine.PorcupineKeyError: PicovoiceKeyError,
    pvrhino.RhinoKeyError: PicovoiceKeyError,
    pvporcupine.PorcupineInvalidStateError: PicovoiceInvalidStateError,
    pvrhino.RhinoInvalidStateError: PicovoiceInvalidStateError,
    pvporcupine.PorcupineRuntimeError: PicovoiceRuntimeError,
    pvrhino.RhinoRuntimeError: PicovoiceRuntimeError,
    pvporcupine.PorcupineActivationError: PicovoiceActivationError,
    pvrhino.RhinoActivationError: PicovoiceActivationError,
    pvporcupine.PorcupineActivationLimitError: PicovoiceActivationLimitError,
    pvrhino.RhinoActivationLimitError: PicovoiceActivationLimitError,
    pvporcupine.PorcupineActivationThrottledError: PicovoiceActivationThrottledError,
    pvrhino.RhinoActivationThrottledError: PicovoiceActivationThrottledError,
    pvporcupine.PorcupineActivationRefusedError: PicovoiceActivationRefusedError,
    pvrhino.RhinoActivationRefusedError: PicovoiceActivationRefusedError,
}


class Picovoice(object):
  
    def __init__(
            self,
            access_key: str,
            keyword_path: str,
            wake_word_callback: Callable[[], None],
            context_path: str,
            inference_callback: Callable[[pvrhino.Inference], None],
            porcupine_library_path: Optional[str] = None,
            porcupine_model_path: Optional[str] = None,
            porcupine_sensitivity: float = 0.5,
            rhino_library_path: Optional[str] = None,
            rhino_model_path: Optional[str] = None,
            rhino_sensitivity: float = 0.5,
            endpoint_duration_sec: float = 1.,
            require_endpoint: bool = True):
       

        if not access_key:
            raise ValueError("access_key should be a non-empty string.")

        if not os.path.exists(keyword_path):
            raise ValueError("Couldn't find Porcupine's keyword file at '%s'." % keyword_path)

        if not callable(wake_word_callback):
            raise ValueError("Invalid wake word callback.")

        if not os.path.exists(context_path):
            raise ValueError("Couldn't find Rhino's context file at '%s'." % context_path)

        if not callable(inference_callback):
            raise ValueError("Invalid inference callback.")

        if porcupine_library_path is not None and not os.path.exists(porcupine_library_path):
            raise ValueError("Couldn't find Porcupine's dynamic library at '%s'." % porcupine_library_path)

        if porcupine_model_path is not None and not os.path.exists(porcupine_model_path):
            raise ValueError("Couldn't find Porcupine's model file at '%s'." % porcupine_model_path)

        if not 0 <= porcupine_sensitivity <= 1:
            raise ValueError("Porcupine's sensitivity should be within [0, 1].")

        if rhino_library_path is not None and not os.path.exists(rhino_library_path):
            raise ValueError("Couldn't find Rhino's dynamic library at '%s'." % rhino_library_path)

        if rhino_model_path is not None and not os.path.exists(rhino_model_path):
            raise ValueError("Couldn't find Rhino's model file at '%s'." % rhino_model_path)

        if not 0 <= rhino_sensitivity <= 1:
            raise ValueError("Rhino's sensitivity should be within [0, 1]")

        if not 0.5 <= endpoint_duration_sec <= 5.:
            raise ValueError("Endpoint duration should be within [0.5, 5]")

        try:
            self._porcupine = pvporcupine.create(
                access_key=access_key,
                library_path=porcupine_library_path,
                model_path=porcupine_model_path,
                keyword_paths=[keyword_path],
                sensitivities=[porcupine_sensitivity])
        except pvporcupine.PorcupineError as e:
            raise _PPN_RHN_ERROR_TO_PICOVOICE_ERROR[type(e)] from e

        self._wake_word_callback = wake_word_callback

        self._is_wake_word_detected = False

        try:
            self._rhino = pvrhino.create(
                access_key=access_key,
                library_path=rhino_library_path,
                model_path=rhino_model_path,
                context_path=context_path,
                sensitivity=rhino_sensitivity,
                endpoint_duration_sec=endpoint_duration_sec,
                require_endpoint=require_endpoint)
        except pvrhino.RhinoError as e:
            raise _PPN_RHN_ERROR_TO_PICOVOICE_ERROR[type(e)] from e

        self._inference_callback = inference_callback

        assert self._porcupine.sample_rate == self._rhino.sample_rate
        self._sample_rate = self._porcupine.sample_rate

        assert self._porcupine.frame_length == self._rhino.frame_length
        self._frame_length = self._porcupine.frame_length

    def delete(self):
        """Releases resources acquired."""

        self._porcupine.delete()
        self._rhino.delete()

    def process(self, pcm: Sequence[int]) -> None:
        
        if len(pcm) != self.frame_length:
            raise ValueError("Invalid frame length. expected %d but received %d" % (self.frame_length, len(pcm)))

        if not self._is_wake_word_detected:
            try:
                self._is_wake_word_detected = self._porcupine.process(pcm) == 0
                if self._is_wake_word_detected:
                    self._wake_word_callback()
            except pvporcupine.PorcupineError as e:
                raise _PPN_RHN_ERROR_TO_PICOVOICE_ERROR[type(e)] from e
        else:
            try:
                is_finalized = self._rhino.process(pcm)
                if is_finalized:
                    self._is_wake_word_detected = False
                    inference = self._rhino.get_inference()
                    self._inference_callback(inference)
            except pvrhino.RhinoError as e:
                raise _PPN_RHN_ERROR_TO_PICOVOICE_ERROR[type(e)] from e

    @property
    def sample_rate(self) -> int:
        """Audio sample rate accepted by Picovoice."""

        return self._sample_rate

    @property
    def frame_length(self) -> int:
        """Number of audio samples per frame."""

        return self._frame_length

    @property
    def version(self) -> str:
        """Version"""

        return '2.2.0'

    @property
    def context_info(self) -> str:
        """Context information."""

        return self._rhino.context_info

    def __str__(self):
        return 'Picovoice %s {Porcupine %s, Rhino %s}' % (self.version, self._porcupine.version, self._rhino.version)


__all__ = [
    'Picovoice',
    'PicovoiceError',
    'PicovoiceMemoryError',
    'PicovoiceIOError',
    'PicovoiceInvalidArgumentError',
    'PicovoiceStopIterationError',
    'PicovoiceKeyError',
    'PicovoiceInvalidStateError',
    'PicovoiceRuntimeError',
    'PicovoiceActivationError',
    'PicovoiceActivationLimitError',
    'PicovoiceActivationThrottledError',
    'PicovoiceActivationRefusedError'
]