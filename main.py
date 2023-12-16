from http import HTTPStatus
from flask import Flask, request, abort
from flask_restful import Resource, Api
from models import Phone as PhoneModel
from engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from tabulate import tabulate

session = Session(engine)

app = Flask(__name__)
api = Api(app)


class BaseMethod():

    def __init__(self):
        self.raw_weight = {'ram': 4, 'storage': 5,
                           'chipset': 5, 'layar': 4, 'harga': 5, 'baterai': 4}

    @property
    def weight(self):
        total_weight = sum(self.raw_weight.values())
        return {k: round(v/total_weight, 2) for k, v in self.raw_weight.items()}

    @property
    def data(self):
        query = select(PhoneModel.id, PhoneModel.nama_smartphone, PhoneModel.ram, PhoneModel.storage, PhoneModel.chipset,
                       PhoneModel.layar, PhoneModel.harga, PhoneModel.baterai)
        result = session.execute(query).fetchall()
        print(result)
        return [{'id': Phone.id, 'nama_smartphone': Phone.nama_smartphone, 'ram': Phone.ram, 'storage': Phone.storage,
                'chipset': Phone.chipset, 'layar': Phone.layar, 'harga': Phone.harga, 'baterai': Phone.baterai} for Phone in result]

    @property
    def normalized_data(self):
        ram_values = []  # max
        storage_values = []  # max
        chipset_values = []  # max
        layar_values = []  # max
        harga_values = []  # min
        baterai_values = []  # max

        for data in self.data:
            # ram
            ram_values.append(data['ram'])

            # storage
            storage_values.append(data['storage'])

            # chipset
            chipset_spec = data['chipset']
            chipset_numeric_values = [
                int(value) for value in chipset_spec.split() if value.isdigit()]
            max_chipset_value = max(
                chipset_numeric_values) if chipset_numeric_values else 1
            chipset_values.append(max_chipset_value)

            # Layar
            layar_spec = data['layar']
            layar_numeric_values = [float(value.split()[0]) for value in layar_spec.split(
            ) if value.replace('.', '').isdigit()]
            max_layar_value = max(
                layar_numeric_values) if layar_numeric_values else 1
            layar_values.append(max_layar_value)

            # harga
            harga_values.append(data['harga'])

            # baterai
            baterai_values.append(data['baterai'])

        return [
            {
                'id': data['id'],
                'ram': data['ram'] / max(ram_values),
                'storage': data['storage'] / max(storage_values),
                'chipset': chipset_value / max(chipset_values),
                'layar': layar_value / max(layar_values),
                'harga': min(harga_values) / data['harga'] if data['harga'] != 0 else 0,
                'baterai': data['baterai'] / max(baterai_values),
            }
            for data, chipset_value, layar_value in zip(self.data, chipset_values, layar_values)
        ]

    def update_weights(self, new_weights):
        self.raw_weight = new_weights


class WeightedProductCalculator(BaseMethod):
    def update_weights(self, new_weights):
        self.raw_weight = new_weights

    @property
    def calculate(self):
        normalized_data = self.normalized_data
        produk = [
            {
                'id': row['id'],
                'produk': row['ram']**self.weight['ram'] *
                row['storage']**self.weight['storage'] *
                row['chipset']**self.weight['chipset'] *
                row['layar']**self.weight['layar'] *
                row['harga']**self.weight['harga'] *
                row['baterai']**self.weight['baterai']
            }
            for row in normalized_data
        ]
        sorted_produk = sorted(produk, key=lambda x: x['produk'], reverse=True)
        sorted_data = [
            {
                'ID': product['id'],
                'score': round(product['produk'], 3)
            }
            for product in sorted_produk
        ]
        return sorted_data


class WeightedProduct(Resource):
    def get(self):
        calculator = WeightedProductCalculator()
        result = calculator.calculate
        return sorted(result, key=lambda x: x['score'], reverse=True), HTTPStatus.OK.value

    def post(self):
        new_weights = request.get_json()
        calculator = WeightedProductCalculator()
        calculator.update_weights(new_weights)
        result = calculator.calculate
        return {'phone': sorted(result, key=lambda x: x['score'], reverse=True)}, HTTPStatus.OK.value


class SimpleAdditiveWeightingCalculator(BaseMethod):
    @property
    def calculate(self):
        weight = self.weight
        result = [
            {
                'ID': row['id'],
                'Score': round(row['ram'] * weight['ram'] +
                               row['storage'] * weight['storage'] +
                               row['chipset'] * weight['chipset'] +
                               row['layar'] * weight['layar'] +
                               row['harga'] * weight['harga'] +
                               row['baterai'] * weight['baterai'], 3)
            }
            for row in self.normalized_data
        ]
        sorted_result = sorted(result, key=lambda x: x['Score'], reverse=True)
        return sorted_result

    def update_weights(self, new_weights):
        self.raw_weight = new_weights


class SimpleAdditiveWeighting(Resource):
    def get(self):
        saw = SimpleAdditiveWeightingCalculator()
        result = saw.calculate
        return sorted(result, key=lambda x: x['Score'], reverse=True), HTTPStatus.OK.value

    def post(self):
        new_weights = request.get_json()
        saw = SimpleAdditiveWeightingCalculator()
        saw.update_weights(new_weights)
        result = saw.calculate
        return {'phone': sorted(result, key=lambda x: x['Score'], reverse=True)}, HTTPStatus.OK.value


class Phone(Resource):
    def get_paginated_result(self, url, list, args):
        page_size = int(args.get('page_size', 10))
        page = int(args.get('page', 1))
        page_count = int((len(list) + page_size - 1) / page_size)
        start = (page - 1) * page_size
        end = min(start + page_size, len(list))

        if page < page_count:
            next_page = f'{url}?page={page+1}&page_size={page_size}'
        else:
            next_page = None
        if page > 1:
            prev_page = f'{url}?page={page-1}&page_size={page_size}'
        else:
            prev_page = None

        if page > page_count or page < 1:
            abort(404, description=f'Data Tidak Ditemukan.')
        return {
            'page': page,
            'page_size': page_size,
            'next': next_page,
            'prev': prev_page,
            'Results': list[start:end]
        }

    def get(self):
        query = session.query(PhoneModel).order_by(PhoneModel.id)
        result_set = query.all()
        data = [{'id': row.id, 'nama_smartphone': row.nama_smartphone, 'ram': row.ram, 'storage': row.storage,
                'chipset': row.chipset, 'layar': row.layar, 'harga': row.harga, 'baterai': row.baterai}
                for row in result_set]
        return self.get_paginated_result('phone/', data, request.args), 200


api.add_resource(Phone, '/phone')
api.add_resource(WeightedProduct, '/wp')
api.add_resource(SimpleAdditiveWeighting, '/saw')

if __name__ == '__main__':
    app.run(port='5005', debug=True)
