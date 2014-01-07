#!/usr/bin/env python

# This file is part of potion.
#
#  potion is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  potion is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with potion. If not, see <http://www.gnu.org/licenses/>.
#
# (C) 2012- by Adam Tauber, <asciimoo@gmail.com>

if __name__ == "__main__":
    from sys import path
    from os.path import realpath, dirname
    path.append(realpath(dirname(realpath(__file__))+'/../'))

from flask import Flask, request, render_template, redirect, flash
from sqlalchemy import not_
from potion.models import db_session, Item, Source, Query
from potion.common import cfg
from flask.ext.wtf import Form
from wtforms import  TextField, SubmitField
from wtforms.validators import Required
from potion.helpers import Pagination


menu_items  = (('/'                 , 'home')
              #,('/doc'              , 'documentation')
              ,('/sources'          , 'sources')
              ,('/queries'          , 'queries')
              ,('/top'              , 'top %s unarchived' % cfg.get('app', 'items_per_page'))
              ,('/saved'            , 'top %s saved' % cfg.get('app', 'items_per_page'))
              ,('/all'              , 'all')
              )

app = Flask(__name__)
app.secret_key = cfg.get('app', 'secret_key')

class SourceForm(Form):
    #name, address, source_type, is_public=True, attributes={}
    name                    = TextField('Name'      , [Required()])
    source_type             = TextField('Type'      , [Required()])
    address                 = TextField('Address'   , [Required()])
    submit                  = SubmitField('Submit'  , [Required()])


@app.context_processor
def contex():
    global menu_items, cfg, query
    return {'menu'              : menu_items
           ,'cfg'               : cfg
           ,'query'             : ''
           ,'path'              : request.path
           ,'menu_path'         : request.path
           ,'unarchived_count'  : Item.query.filter(Item.archived==False).count()
           ,'item_count'        : Item.query.count()
           }

def parse_query(q):
    return q.get('query')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html'
                          ,sources  = Source.query.all()
                          ,unreads  = Item.query.filter(Item.archived==False).count()
                          )

def get_unarchived_ids(items):
    return [item.item_id for item in items if item.archived == False]

def get_saved_ids(items):
    return [item.item_id for item in items if item.saved == True]

@app.route('/doc', methods=['GET'])
def doc():
    return 'TODO'

@app.route('/saved', methods=['GET'])
@app.route('/saved/<int:page_num>', methods=['GET'])
def saved(page_num=1):
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = Item.query.filter(Item.saved==True).order_by(Item.added).limit(limit).offset(offset).all()
    items.reverse()
    pagination = Pagination(page_num, limit, Item.query.filter(Item.saved==True).count())
    return render_template('flat.html'
                          ,items        = items
                          ,pagination   = pagination
                          ,unsaveds     = get_saved_ids(items)
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path    = '/saved' #preserve menu highlight when paging
                          )

@app.route('/top', methods=['GET'])
@app.route('/top/<int:page_num>', methods=['GET'])
def top(page_num=1):
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = Item.query.filter(Item.archived==False).order_by(Item.added).limit(limit).offset(offset).all()
    pagination = Pagination(page_num, limit, Item.query.filter(Item.archived==False).count())
    return render_template('flat.html'
                          ,items        = items
                          ,pagination   = pagination
                          ,unsaveds     = get_saved_ids(items)
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path    = '/top' #preserve menu highlight when paging
                          )

@app.route('/sources', methods=['GET', 'POST'])
def sources():
    form = SourceForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            s = Source(form.name.data, form.source_type.data, form.address.data)
            db_session.add(s)
            db_session.commit()
        except Exception, e:
            flash('[!] Insertion error: %r' % e)
            db_session.rollback()
            return redirect('/sources')
        flash('Source "%s" added' % form.name.data)
        return redirect(request.referrer or '/')
    return render_template('sources.html'
                          ,form     = form
                          ,sources  = Source.query.all()
                          ,mode     = 'add'
                          )

@app.route('/sources/<int:s_id>', methods=['GET', 'POST'])
def source_modify(s_id=0):
    source=Source.query.get(s_id)
    form=SourceForm(obj=source)
    if request.method == 'POST' and form.validate():
        source.name=form.name.data
        source.source_type=form.source_type.data
        source.address=form.address.data
        db_session.add(source)
        db_session.commit()
        flash('Source "%s" modified' % form.name.data)
        return redirect('/sources')
    return render_template('sources.html'
                          ,form     = form
                          ,sources  = Source.query.all()
                          ,mode     = 'modify'
                          ,menu_path= '/sources' #preserve menu highlight when paging
                          )

@app.route('/sources/delete/<int:s_id>', methods=['GET'])
def del_source(s_id):
    Source.query.filter(Source.source_id==s_id).delete()
    db_session.commit()
    flash('Source removed')
    return redirect(request.referrer or '/')

@app.route('/all')
@app.route('/all/<int:page_num>')
def all(page_num=1):
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = Item.query.order_by(Item.added).limit(limit).offset(offset).all()
    pagination = Pagination(page_num, limit, Item.query.count())
    return render_template('flat.html'
                          ,pagination   = pagination
                          ,items        = items
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path= '/all'
                          )

@app.route('/queries', methods=['GET'])
def queries():
    items = []
    return render_template('queries.html'
                          ,queries      = Query.query.all()
                          ,items        = items
                          )

@app.route('/query', methods=['POST'])
def query_redirect():
    q_str = request.form.get('query')
    return redirect('/query/'+q_str)

@app.route('/query/<path:q_str>', methods=['GET'])
def do_query(q_str):
    page_num = 1
    if(q_str.find('/')):
        try:
            page_num = int(q_str.split('/')[-1])
            q_str = ''.join(q_str.split('/')[:-1])
        except:
            pass

    #if(q_str.startswith('!')):
    #    q_str = q_str[1:]
    #    reverse = True

    rules = q_str.split(',')
    query = db_session.query(Item).filter(Item.source_id==Source.source_id)
    for rule in rules:
        if rule.find(':') != -1:
            item, value = rule.split(':', 1)
            if item.startswith('~'):
                query = query.filter(getattr(Item, item[1:]).contains(value))
            elif item.startswith('-'):
                query = query.filter(not_(getattr(Item, item[1:]).contains(value)))
            else:
                query = query.filter(getattr(Item, item) == value)
            continue
        if rule.startswith('_'):
            query = query.filter(Source.name == rule[1:])
            continue
    count = query.count()
    limit = int(cfg.get('app', 'items_per_page'))
    offset = limit*(page_num-1)
    items = query.limit(limit).offset(offset).all()
    #if reverse:
    #    items.reverse()

    pagination = Pagination(page_num, limit, count)
    return render_template('flat.html'
                          ,pagination   = pagination
                          ,items        = items
                          ,unarchiveds  = get_unarchived_ids(items)
                          ,menu_path    = '/query/%s' % q_str
                          )

@app.route('/archive', methods=['POST'])
@app.route('/archive/<int:id>', methods=['GET'])
def archive(id=0):
    if request.method=='POST':
        try:
            ids = map(int, request.form.get('ids', '').split(','))
        except:
            flash('Bad params')
            return redirect(request.referrer or '/')
    elif id==0:
        flash('Nothing to archive')
        return redirect(request.referrer or '/')
    else:
        ids=[id]
    db_session.query(Item).filter(Item.item_id.in_(ids)).update({Item.archived: True}, synchronize_session='fetch')
    db_session.commit()
    if id:
        return render_template('status.html', messages=['item(%s) archived' % id])
    flash('Successfully archived items: %d' % len(ids))
    return redirect(request.referrer or '/')

@app.route('/opml', methods=('GET',))
def opml():
    return render_template('opml.xml'
                           ,sources = Source.query.filter(Source.source_type=='feed').all()
                           )

@app.route('/save', methods=['POST'])
@app.route('/save/<int:save_id>', methods=['GET'])
def save(save_id=0):
    db_session.query(Item).filter(Item.item_id==save_id).update({Item.saved: True}, synchronize_session='fetch')
    db_session.commit()
    if save_id:
        return render_template('status.html', messages=['item(%s) saved' % save_id])
    flash('Successfully saved item')
    return redirect(request.referrer or '/')


@app.route('/opml/import', methods=['GET'])
def opml_import():
    url = request.args.get('url')
    if not url:
        return 'Missing url'
    import opml
    try:
        o = opml.parse(url)
    except:
        return 'Cannot parse opml file %s' % url

    def import_outline_element(o):
        for f in o:
            if hasattr(f,'xmlUrl'):
                s = Source(f.title,'feed',f.xmlUrl)
                db_session.add(s)
            else:
                import_outline_element(f)

    import_outline_element(o)
    db_session.commit()
    flash('import successed')
    return redirect(request.referrer or '/')


if __name__ == "__main__":
    app.run(debug        = cfg.get('server', 'debug')
           ,use_debugger = cfg.get('server', 'debug')
           ,port         = int(cfg.get('server', 'port'))
           )
