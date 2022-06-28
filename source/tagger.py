# SOURCE_MARKER_BEGIN_import
import nltk
from forte.processors.base import PackProcessor
from forte.data.data_pack import DataPack
from ft.onto.base_ontology import Token

# SOURCE_MARKER_END_import


# SOURCE_MARKER_BEGIN_class
class NLTKPOSTagger(PackProcessor):
    r"""A wrapper of NLTK pos tagger."""

    def initialize(self, resources, configs):
        super().initialize(resources, configs)
        # download the NLTK average perceptron tagger
        nltk.download("averaged_perceptron_tagger")

    def _process(self, input_pack: DataPack):
        # get a list of token data entries from `input_pack`
        # using `DataPack.get()`` method
        token_texts = [token.text for token in input_pack.get(Token)]

        # use nltk pos tagging module to tag token texts
        taggings = nltk.pos_tag(token_texts)

        # assign nltk taggings to token attributes
        for token, tag in zip(input_pack.get(Token), taggings):
            token.pos = tag[1]


# SOURCE_MARKER_END_class
