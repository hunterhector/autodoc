# SOURCE_MARKER_BEGIN_import
from forte import Pipeline

from forte.data.readers import StringReader
from fortex.spacy import SpacyProcessor

# SOURCE_MARKER_END_import

# SOURCE_MARKER_BEGIN_pipeline
pipeline: Pipeline = Pipeline[DataPack]()
pipeline.set_reader(StringReader())
pipeline.add(SpacyProcessor(), {"processors": ["sentence", "tokenize"]})
pipeline.add(NLTKPOSTagger())

input_string = "Forte is a data-centric ML framework"
for pack in pipeline.initialize().process_dataset(input_string):
    for sentence in pack.get("ft.onto.base_ontology.Sentence"):
        print("The sentence is: ", sentence.text)
        print("The POS tags of the tokens are:")
        for token in pack.get(Token, sentence):
            print(f" {token.text}[{token.pos}]", end=" ")
        print()
# SOURCE_MARKER_END_pipeline
