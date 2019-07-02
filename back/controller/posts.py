#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by Administrator at 2019/6/29 15:18
import random
from flask import g
from sqlalchemy import func

from back import setting
from back.controller import categories
from back.controller import tags, category_for_post, assert_new_tag_in_tags
from back.models import User, ArticleBody, Article, Tag, db
from back.utils import DateTime

date_maker = DateTime()


def posts_order_by_date(desc=True):
    if desc:
        posts_query = Article.query.order_by(Article.create_date.desc())
    else:
        posts_query = Article.query.order_by(Article.create_date)
    return posts_query


def posts_order_by_view_counts(desc=True):
    if desc:
        posts_query = Article.query.order_by(Article.view_counts.desc())
    else:
        posts_query = Article.query.order_by(Article.view_counts)
    return posts_query


def make_limit(query_data, limit_count):
    """
    是否对数量限制
    :param query_data:
    :param limit_count:
    :return:
    """
    if limit_count >= 1:
        posts = query_data.limit(limit_count).all()
    else:
        posts = query_data.all()
    data = post_info_json(posts)
    return data


def make_paginate(query_data, page=None, per_page=None):
    """
    返回分页对象
    :param query_data:
    :param page:
    :param per_page:
    :return:
    """
    assert all([page, per_page])
    pagination = query_data.paginate(
        page, per_page=per_page, error_out=False
    )
    return pagination


def post_info_json(posts):
    """
    返回id与title键值对
    :param posts:list,
    :return: list,
    """
    ret_data = []
    for post in posts:
        post_info = dict()
        post_info['id'] = post.post_id
        post_info['post_url_id'] = post.identifier
        post_info['title'] = post.title
        ret_data.append(post_info)
    return ret_data


def post_detail(post_info):
    """
    用户点击文章链接跳详情页的数据接口，返回在这里找
    :param post_info:
    :return:
    """
    user_id = post_info.author_id
    user_info = user_info_for_post(user_id)
    body_id = post_info.body_id
    body_info = content_for_post(body_id)
    category_id = post_info.category_id
    category_info = category_for_post(category_id)
    post_id = post_info.post_id
    tags_info = tags_for_post(post_id)['tags_info']
    str_date = ''
    create_date = post_info.create_date
    if create_date:
        str_date = date_maker.make_strftime(create_date)
    json_post = {
        "author": user_info,
        "body": body_info,
        "category": category_info,
        # TODO:后期添加
        "commentCounts": 0,
        "createDate": str_date,
        "id": post_id,
        # TODO:摘要，暂无；感觉这个api不需要该参数？？？
        # "summary": "本节将介绍如何在项目中使用 Element。",
        "tags": tags_info,
        "title": post_info.title,
        "viewCounts": post_info.view_counts,
        "weight": post_info.weight,
    }
    return json_post


def makeup_post_item_for_index(posts):
    """
    组装首页展示需要的数据
    :return:
    """
    '''
    [{
    "author":{
        "nickname":"imoyao"
    },
    "commentCounts":0,
    "createDate":"2019.02.28 15:37",
    "id":28,
    "summary":"sample summary",
    "tags":[
        {
            "tagname":"Python"
        }
    ],
    "title":"tt",
    "viewCounts":188,
    "weight":0
    },
    ……
    {……}
    ]
    '''
    post_list = []
    shown_user_info = dict()

    for post_item in posts:
        user_id = post_item.author_id
        str_date = ''
        create_date = post_item.create_date
        if create_date:
            str_date = date_maker.make_strftime(create_date)
        str_user_id = str(user_id) if isinstance(user_id, int) else user_id
        # 一般来说：post数量大于user数量，所以我们这里在获取用户信息时先判断一下是否已经获取到了，没有回去到的话再去数据库中查询
        already_got = shown_user_info.get(str_user_id)
        if already_got:
            user_info = shown_user_info[str_user_id]
        else:
            user_info = user_info_for_post(user_id)
            shown_user_info[str_user_id] = user_info
        username = user_info['nickname']
        post_id = post_item.post_id
        tag_infos = tags_for_post(post_id)['tags_info']
        post_content = content_for_post(post_id)
        print('----post_content------', post_content)
        summary = post_content.get('summary') or ''
        tags = []
        if tag_infos:
            tags = [{'tagname': tag.get('tag_name') or ''} for tag in tag_infos]
        post_info = {
            "author": {
                "nickname": username
            },
            # TODO: 继续开发
            "commentCounts": 0,
            "createDate": str_date,
            "id": post_item.post_id,
            "summary": summary,
            "tags": tags,
            "title": post_item.title,
            "viewCounts": post_item.view_counts,
            "weight": post_item.weight
        }
        post_list.append(post_info)
    return post_list


def user_info_for_post(user_id):
    """
    文章作者信息
    :param user_id: str(number),author_id
    :return: dict,
    """
    user = User.query.get(user_id)
    if user:
        return {'avatar': user.avatar_hash,
                'id': user_id,
                'nickname': user.username,
                }


def content_for_post(body_id):
    """
    获取文章正文内容
    TODO: 因为此处返回表所有的数据，所以是否可以直接返回，不需要手动组装（只是修改前端获取的字段键）
    :param body_id: str(number)
    :return: dict
    """
    body = ArticleBody.query.get(body_id)
    # https://stackoverflow.com/questions/5022066/how-to-serialize-sqlalchemy-result-to-json
    if body:
        return {'id': body_id,
                'content': body.content,
                'contentHtml': body.content_html,
                'summary': body.summary,
                }


def tags_for_post(post_id):
    """
    根据文章 id 查找对应的 tags 信息
    ref:https://github.com/mrjoes/flask-admin/blob/402b56ea844dc5b215f6293e7dc63f39a6723692/examples/sqla/app.py
    https://www.jianshu.com/p/cd5b1728832c
    通过文章获取标签信息，重点在`posts_tags_table`的创建
    :param post_id: int,
    :return: dict,
    """
    article_obj = Article.query.filter(Article.post_id == post_id).first()
    tags_data = article_obj.tags
    tags_info = []
    if tags_data:
        # 标签信息列表
        tags_info = [{'id': tag.id, 'tag_name': tag.tag_name} for tag in tags_data]
    tag_count = len(tags_info)

    data = {
        'id': post_id,
        'tags_info': tags_info,
        'tag_count': tag_count
    }
    return data


class PostNewArticle:
    # TODO: 其他 controllers 也应该这么写
    """
    创建新博文
    """

    @staticmethod
    def new_post_body(summary, content_html, content):
        body = ArticleBody(summary=summary, content=content, content_html=content_html)
        db.session.add(body)
        db.session.commit()
        return body.id

    @staticmethod
    def gen_post_identifier():
        """
        生成新的文章标识码
        规则：找到现有最大值，然后加随机数
        :return: int
        """
        # (19930126,)[0]
        max_identifier = db.session.query(func.max(Article.identifier)).one_or_none()
        if max_identifier:
            max_num = max_identifier[0]
            increase_int = random.randrange(1, 5)
            post_identifier = max_num + increase_int
        else:
            post_identifier = setting.INITIAL_POST_IDENTIFIER
        return post_identifier

    def new_post_action(self, category_id, all_tags_for_new_post, title, body_id, weight=0):
        """
        添加一篇博文
        :param category_id: int,
        :param all_tags_for_new_post: list
        :param title: str,
        :param body_id: int
        :param weight:
        :return:
        """
        new_identifier = self.gen_post_identifier()
        print('-----g.user.id------', g)
        # print('-----g.user.id------', g.user.id)
        author_id = '1'  # TODO: just for test
        post = Article(title=title, identifier=new_identifier, author_id=author_id, body_id=body_id,
                       view_counts=setting.INITIAL_VIEW_COUNTS,
                       weight=weight, category_id=category_id)
        print('-----all_tags_for_new_post', all_tags_for_new_post)
        need_add_tags = assert_new_tag_in_tags(all_tags_for_new_post)
        # TODO:正常函数不应该走到这里，因为前面已经添加了用户自主添加的，此处主要是刚开始写的代码不完善
        if need_add_tags:
            tags.new_multi_tags(need_add_tags)
        for tag_name in all_tags_for_new_post:
            # tag_obj = Tag.query.filter_by(tag_name=tag_name).first()
            # TODO: next line is right
            tag_obj = Tag.query.filter_by(tag_name=tag_name).one()
            post.tags.append(tag_obj)

        db.session.add(post)
        db.session.commit()
        post_id = post.post_id
        print('post_id', 'post_id')
        return post_id

    def new_post(self, category_name, summary, content_html, content, title, weight=0, category_description='',
                 post_tags=None,
                 category_id=None):
        """
        POST 博文，需要先看是否要 POST category、tag；然后 POST body；最后操作 Article 表
        :param category_name:str,
        :param category_description:str,
        :param summary:str,
        :param content_html:str,
        :param content:str,
        :param title:str,
        :param weight:int #TODO:bool? int?
        :param post_tags:list,
        :param category_id:int,
        :return:int,new_post_id
        """
        all_tags_for_new_post = None

        if not category_id and category_name:
            category_id = categories.new_category(category_name, category_description)

        if post_tags:
            all_tags_for_new_post = tags.add_tag_for_post(post_tags)

        body_id = self.new_post_body(summary, content_html, content)

        new_post_id = self.new_post_action(category_id, all_tags_for_new_post, title, body_id, weight=weight)

        return new_post_id
