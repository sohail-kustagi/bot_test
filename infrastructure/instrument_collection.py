import json
from db.db import DataDB
from models.instrument import Instrument


class InstrumentCollection:
    FILENAME = "instruments.json"
    API_KEYS = ['Symbol', 'Precision', 'TradeAmountStep']

    def __init__(self):
        self.instruments_dict = {}

    def LoadInstruments(self, path):
        """
        Load instruments from a JSON file into the instruments_dict.
        :param path: Path to the directory containing the instruments.json file.
        """
        self.instruments_dict = {}
        fileName = f"{path}/{self.FILENAME}"
        try:
            with open(fileName, "r") as f:
                data = json.loads(f.read())
                for k, v in data.items():
                    self.instruments_dict[k] = Instrument.FromApiObject(v)
            print(f"[DEBUG] Loaded instruments: {list(self.instruments_dict.keys())}")
        except FileNotFoundError:
            print(f"[ERROR] Instruments file not found: {fileName}")
        except Exception as e:
            print(f"[ERROR] Failed to load instruments: {e}")

    def LoadInstrumentsDB(self):
        self.instruments_dict = {}
        data = DataDB().query_single(DataDB.INSTRUMENTS_COLL)
        for k, v in data.items():
            self.instruments_dict[k] = Instrument.FromApiObject(v)

    def CreateFile(self, data, path):
        if data is None:
            print("Instrument file creation failed")
            return

        instruments_dict = {}
        for i in data:
            key = i['Symbol']
            instruments_dict[key] = {k: i[k] for k in self.API_KEYS}

        fileName = f"{path}/{self.FILENAME}"
        with open(fileName, "w") as f:
            f.write(json.dumps(instruments_dict, indent=2))

    def CreateDB(self, data):
        if data is None:
            print("Instrument file creation failed")
            return

        instruments_dict = {}
        for i in data:
            key = i['Symbol']
            instruments_dict[key] = {k: i[k] for k in self.API_KEYS}

        database = DataDB()
        database.delete_many(DataDB.INSTRUMENTS_COLL)
        database.add_one(DataDB.INSTRUMENTS_COLL, instruments_dict)

    def PrintInstruments(self):
        [print(k, v) for k, v in self.instruments_dict.items()]
        print(len(self.instruments_dict.keys()), "instruments")


# Initialize the global instrument collection
instrumentCollection = InstrumentCollection()
