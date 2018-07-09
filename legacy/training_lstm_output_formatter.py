from rlbot.utils.logging_utils import get_logger

from legacy.legacy_input_formatter import LegacyInputFormatter
import numpy as np

from legacy.legacy_output_formatter import LegacyOutputFormatter


class TrainingLSTMOutputFormatter(LegacyOutputFormatter):
    sequence_size = 100

    def create_array_for_training(self, output_array, batch_size=1):
        new_size = batch_size / self.sequence_size
        return np.reshape(output_array, [int(new_size), self.sequence_size, self.get_model_output_dimension()])
