# -*- coding: UTF-8 -*-

import os
import xlrd
import time
import tarfile
from flask import Flask, render_template, send_from_directory, request

from model_propertys import ModelPropertys, large_str

app = Flask(__name__)


# 首页
@app.route('/')
def index():
    return render_template('create_class.html')


# 下载
@app.route("/result/<filename>", methods=['GET'])
def downloader(filename):
    # 指定文件下载目录，默认为当前项目根路径
    dirpath = os.path.join(app.root_path, 'result')
    # as_attachment=True 表示下载
    return send_from_directory(dirpath, filename, as_attachment=True)


# 生成方法
@app.route('/createClass', methods=['GET', 'POST'])
def create_class():
    file_name = msg = column_array = None
    class_name = package = description = ''
    sql_str = kind = ''
    table_name = ''
    model_property_list = model_column_list = temp_list =[]
    type_str_strat = name_str_strat = None
    type_str = name_str = context_str = ''

    d = time.strftime("%Y-%m-%d", time.localtime())
    sndclass = request.form.get('sndclass')
    provider = request.form.get('provider')
    model = request.form.get('model')
    dao = request.form.get('dao')

    # 读取输入文件
    excel_data = xlrd.open_workbook("input.xls")
    table = excel_data.sheet_by_index(0)
    for rowNum in range(table.nrows):
        if rowNum < 18:
            continue

        rowVale = table.row_values(rowNum)
        if rowVale[2] != '':
            if rowVale[2] == 'SndDealer':
                kind = 'deal'
            elif rowVale[2] == 'SndVender':
                kind = 'vend'
            else:
                kind = ''
        description = rowVale[3]
        class_name = rowVale[4]
        column_array = rowVale[5].split('\n')
        for out in column_array:
            type_str_strat = out.find('char') + len('char')
            type_str = (out)[:type_str_strat].strip()
            name_str_strat = out.find(';') + len(';')
            name_str = (out)[type_str_strat:name_str_strat].strip()
            context_str = (out)[name_str_strat:].strip()
            model_property_list.append(ModelPropertys(type_str, name_str, context_str))

        model_column_list = rowVale[6].split('\n')
        model_column_list = [x.replace(',', '').strip() for x in model_column_list]
        sql_str = rowVale[7]
        if sql_str == '':
            continue
        table_name = rowVale[9]
        if table_name == '':
            continue
        else:
            table_name = (table_name)[table_name.find('.') + len('.'):]
            temp_list = table_name.split('_')
            temp_list = [large_str(x) for x in temp_list]
            table_name = "".join(temp_list)

        # 调用创建provider
        if provider and len(provider) >= 1:
            print('--- create provider class')
            package = 'com.dao.provider'
            create_provider(class_name, table_name, package, d, sql_str)
            file_name = make_targz()

        # 调用创建model
        if model and len(model) >= 1:
            print('--- create model class')
            package = 'com.model'
            create_model(class_name, package, model_property_list, d)

        # 调用创建dao
        if dao and len(dao) >= 1:
            print('--- create dao class')
            package = 'com.dao'
            create_dao(class_name, table_name, package, model_property_list, model_column_list, d)

        # 调用创建sndclass
        if sndclass and len(sndclass) >= 1:
            print('--- create sndclass class')
            package = 'com.lpmssnd.' + kind
            create_sndclass(class_name, table_name, package, d, description)
            file_name = make_targz()

    return render_template('create_class.html', msg=msg, file_name=file_name)


# 创建sndclass
def create_sndclass(class_name, table_name, package, date, description):
    c = {'package': package,
         'class_name': class_name,
         'table_name': table_name,
         'date': date,
         'description': description}
    s = render_template('sndclass_templates.html', **c)
    create_java_file(class_name + 'Class', package, s)


# 创建model
def create_model(class_name, package, columns, date):
    propertys = ''
    formats = format_items = ''
    methods = ''
    if columns:
        for column in columns:
            propertys += '\t' + 'private %s %s; %s' % (column.type, column.name, column.context) + '\n\n'
            format_items += ',' + column.name
            if column.type == 'String':
                formats += '%s'
            elif column.type == 'int':
                formats += '%d'
        methods = 'return String.format("%s"%s);' % (formats, format_items)
    c = {'package': package,
         'class_name': class_name,
         'propertys': propertys,
         'methods': methods,
         'date': date}
    s = render_template('model_templates.html', **c)
    create_java_file(class_name, package, s)


# 创建Dao
def create_dao(class_name, table_name, package, properties, columns, date):
    results_str = format_str = ''

    if columns and properties and len(columns) == len(properties):
        for index in range(len(columns)):
            format_str += '\t\t@Result(property = "%s", column = "%s"),\n' % (properties[index].name, columns[index])
        results_str = '@Results({\n%s\t})' % format_str
    c = {'package': package,
         'class_name': class_name,
         'table_name': table_name,
         'results_str': results_str,
         'date': date}
    s = render_template('dao_templates.html', **c)
    create_java_file(class_name + 'Dao', package, s)


# 创建provider
def create_provider(class_name, table_name, package, date, sql_str):
    c = {'package': package,
         'class_name': class_name,
         'table_name': table_name,
         'date': date,
         'sql_str': sql_str}
    s = render_template('provider_templates.html', **c)
    create_java_file(class_name + 'DaoProvider', package, s)


# 创建java文件
def create_java_file(class_name, package, text, suffix='.java'):
    dirs = os.getcwd() + '/result/' + package.replace('.', '/')+'/'
    if not os.path.exists(dirs):
        os.makedirs(dirs, 0o777)
    fd = os.open(dirs + class_name + suffix, os.O_WRONLY | os.O_CREAT)
    os.write(fd, text.encode(encoding="utf-8", errors="strict"))
    os.close(fd)


#生成tar.gz压缩包
def make_targz():
    file_name = 'com.tar.gz'
    source_dir = os.getcwd() + '/result'
    file_path = source_dir + '/' +'com.tar.gz'
    with tarfile.open(file_path, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
    return file_name


if __name__ == '__main__':
    app.run()
