#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.http import Request
from scrapy.selector import Selector

from tabebot.items import BusinessItem, ReviewItem, UserItem

from pyquery import PyQuery


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def convert_to_float_if_float(s):
    try:
        return float(s)
    except ValueError:
        return s


def convert_to_int_if_int(s):
    try:
        return int(s)
    except ValueError:
        return s


def set_value_if_true(dictionary, key, value):
    if value:
        dictionary[key] = value


class TabelogSpider(CrawlSpider):
    name = 'tabebot'
    allowed_domains = ['tabelog.com']
    download_delay = 1.0

    prefectures = [
        'hokkaido',
        'aomori',
        'iwate',
        'miyagi',
        'akita',
        'yamagata',
        'fukushima',
        'ibaraki',
        'tochigi',
        'gunma',
        'saitama',
        'chiba',
        'tokyo',
        'kanagawa',
        'niigata',
        'toyama',
        'ishikawa',
        'fukui',
        'yamanashi',
        'nagano',
        'gifu',
        'shizuoka',
        'aichi',
        'mie',
        'shiga',
        'kyoto',
        'osaka',
        'hyogo',
        'nara',
        'wakayama',
        'tottori',
        'shimane',
        'okayama',
        'hiroshima',
        'yamaguchi',
        'tokushima',
        'kagawa',
        'ehime',
        'kochi',
        'fukuoka',
        'saga',
        'nagasaki',
        'kumamoto',
        'oita',
        'miyazaki',
        'kagoshima',
        'okinawa',
    ]

    categories = [
        'japanese',   # 日本料理
        'RC0102',     # 寿司・魚介類
        'RC0103',     # 天ぷら・揚げ物
        'RC0104',     # そば・うどん・麺類
        'RC0105',     # うなぎ・どじょう
        'RC0106',     # 焼鳥・串焼・鳥料理
        'RC0107',     # すき焼き・しゃぶしゃぶ
        'RC0108',     # おでん
        'RC0109',     # お好み焼き・たこ焼き
        'RC0110',     # 郷土料理
        'RC0111',     # 丼もの
        'RC0199',     # 和食（その他）
        'RC0201',     # ステーキ・ハンバーグ
        'RC0203',     # 鉄板焼き
        'RC0202',     # パスタ・ピザ
        'hamburger',  # ハンバーガー
        'RC0209',     # 洋食・欧風料理
        'french',     # フレンチ
        'italian',    # イタリアン
        'RC0219',     # 西洋各国料理
        'RC0301',     # 中華料理
        'RC0302',     # 餃子・肉まん
        'RC0303',     # 中華粥
        'RC0304',     # 中華麺
        'korea',      # 韓国料理
        'RC0402',     # 東南アジア料理
        'RC0403',     # 南アジア料理
        'RC0404',     # 西アジア料理
        'RC0411',     # 中南米料理
        'RC0412',     # アフリカ料理
        'RC0499',     # アジア・エスニック（その他）
        'RC1201',     # カレーライス
        'RC1202',     # 欧風カレー
        'RC1203',     # インドカレー
        'RC1204',     # タイカレー
        'RC1205',     # スープカレー
        'RC1299',     # カレー（その他）
        'RC1301',     # 焼肉・ホルモン
        'RC1302',     # ジンギスカン
        'nabe',       # 鍋
        'izakaya',    # 居酒屋
        'RC2102',     # ダイニングバー
        'RC2199',     # 居酒屋・ダイニングバー（その他）
        'RC9901',     # 定食・食堂
        'RC9902',     # 創作料理・無国籍料理
        'RC9903',     # 自然食・薬膳
        'RC9904',     # 弁当・おにぎり
        'RC9999',     # レストラン（その他）
        'ramen',      # ラーメン
        'MC11',       # つけ麺
        'SC0101',     # パン
        'SC0201',     # 洋菓子
        'SC0202',     # 和菓子・甘味処
        'SC0203',     # 中華菓子
        'SC0299',     # スイーツ（その他）
    ]

    start_urls = [
        'http://tabelog.com/{0}/rstLst/{1}/?SrtT=rt&Srt=D'.format(prefecture, category)
        for prefecture in prefectures for category in categories]

    rules = [
        # Follow business list pagination
        Rule(LxmlLinkExtractor(allow=(r'.com/[a-z]+/rstLst/RC\d+/\d+/\?.*',),
                               deny=(r's.tabelog.com')),
             follow=True),

        # Extract business
        Rule(LxmlLinkExtractor(allow=(r'.com/[a-z]+/A\d{4}/A\d{6}/\d+/$',),
                               deny=(r's.tabelog.com')),
             callback='parse_business'),

        # Follow review list pagination (first page)
        Rule(LxmlLinkExtractor(allow=(r'.com/[a-z]+/A\d{4}/A\d{6}/\d+/dtlrvwlst/$',),
                               deny=(r's.tabelog.com')),
             follow=True),

        # COND-0 すべての口コミ
        # COND-1 夜の口コミ
        # COND-2 昼の口コミ

        # smp0 簡易リスト
        # smp1 通常
        # smp2 全文

        # Follow review list pagination and extract reviews
        Rule(LxmlLinkExtractor(allow=(r'.com/[a-z]+/A\d{4}/A\d{6}/\d+/dtlrvwlst/COND-0/smp1/\?.+PG=.+',),
                               deny=(r'favorite_rvwr', r's.tabelog.com')),
             follow=True, callback='parse_reviews_and_users'),
    ]

    def is_tabelog(self, response):
        selector = Selector(response)
        return bool(selector.xpath("//a[@class='p-header__logo-img']/text()"))

    def parse_reviews_and_users(self, response):
        if not self.is_tabelog(response):
            return Request(url=response.url, dont_filter=True)
        
        dom = PyQuery(response.body)
        review_nodes = dom('div.rvw-item')
        business_id = int(re.findall(r'[a-z]+/A\d{4}/A\d{6}/(\d+)/dtlrvwlst/', response.url)[0])
        
        reviews_and_users = []
        for review_node in review_nodes:
            user_id = self._extract_user_id(review_node)
            review = self._generate_review(review_node, business_id, user_id)
            if review:
                reviews_and_users.append(review)
            #user = self._generate_user(review_node, user_id)
            #if user:
            #    reviews_and_users.append(user)
        return reviews_and_users

    def _extract_user_id(self, review_node):
        user_link = review_node.cssselect('.rvw-item__rvwr-name > a:first-child')
        if user_link:
            url = user_link[0].attrib['href']
            return re.findall(r'rvwr/(.+)/', url)[0]

    def _generate_review(self, review_node, business_id, user_id):
        review = ReviewItem()

        review['review_id'] = int(re.findall(r'[a-z]+/A\d{4}/A\d{6}/\d+/dtlrvwlst/B(\d+)', review_node.attrib['data-detail-url'])[0])
        review['business_id'] = business_id
        set_value_if_true(review, 'user_id', user_id)

        visits = review_node.cssselect('.rvw-item__visit-count-num')
        if visits:
            review['visit'] = visits[0].text
        review['text'] = [sentence for sentence in review_node.cssselect('div.rvw-item__rvw-comment > p')[0].itertext()]
        title = review_node.cssselect('a.rvw-item__title-target')
        if title:
            review['title'] = title[0].text_content().strip()

        for meal in ['dinner', 'lunch']:
            css = 'dd.rvw-item__usedprice-data > span.c-rating__time--{0}'.format(meal)
            price = review_node.cssselect(css)
            if price:
                review['price_{0}'.format(meal)] = price[0].getnext().text_content()

            set_value_if_true(review, 'stars_{0}'.format(meal),
                              self._extract_stars(review_node, meal))
        #review['situations'] = self._extract_situations(review_node)
        return review

    def _extract_stars(self, review_node, meal):
        ratings = review_node.cssselect('li.rvw-item__ratings-item')
        if not ratings:
            return
        stars = {}
        for rating in ratings:
            span = rating.cssselect('span.c-rating__time--{0}'.format(meal))
            if not span:
                continue

            stars['total'] = convert_to_float_if_float(rating.cssselect('b.c-rating__val')[0].text)

            lis = rating.cssselect('ul.rvw-item__ratings-dtlscore > li')
            for li, criterion in zip(lis, ['taste', 'service', 'ambience', 'cp', 'drink']):
                score = li.cssselect('strong.rvw-item__ratings-dtlscore-score')[0].text
                stars[criterion] = convert_to_float_if_float(score)

        return stars

    def _extract_situations(self, review_node):
        imgs = review_node.cssselect('p.rvw-item__situation > img')
        situations = []
        for img, situation in zip(imgs, ['friends', 'date', 'settai', 'party', 'family', 'alone']):
            if not img.attrib['src'].endswith('_g.gif'):
                situations.append(situation)
        return situations

    def _generate_user(self, review_node, user_id):
        user = UserItem()

        user['user_id'] = user_id
        user['name'] = review_node.cssselect('.rvw-item__rvwr-name > a > span')[0].text.strip()
        counts = review_node.cssselect('.rvw-item__rvwr-rvwcount')
        if counts:
            count = counts[0].text
            count_candidates = re.findall(r'\d+', count)
            if count_candidates:
                user['review_count'] = int(count_candidates[0])

        profile = review_node.cssselect('.rvw-item__rvwr-profile')
        if profile:
            user['profile'] = profile[0].text_content().strip()
        user['verified'] = bool(review_node.cssselect('.mark-auth-mobile'))
        return user

    def parse_business(self, response):
        if not self.is_tabelog(response):
            return Request(url=response.url, dont_filter=True)

        selector = Selector(response)

        business = BusinessItem()
        
        business['business_id'] = int(re.findall(r'[a-z]+/A\d{4}/A\d{6}/(\d+)/', response.url)[0])
        
        if selector.xpath("//div[@class='rstinfo-table']/table/tbody/tr/td/text()"):
            business['name'] = selector.xpath("//div[@class='rstinfo-table']/table/tbody/tr/td/text()")[0].extract().strip()
        elif selector.xpath("//div[@class='rd-header__headline']/h2/a/text()"):
            business['name'] = selector.xpath("//div[@class='rd-header__headline']/h2/a/text()")[0].extract().strip()
        elif selector.xpath("//div[@class='rd-header__headline']/h2/small/text()"):
            business['name'] = selector.xpath("//div[@class='rd-header__headline']/h2/small/text()")[0].extract().strip()
        
        cats = selector.xpath("//dd[@class='rdheader-subinfo__item-text']//a[starts-with(@href,'https://tabelog.com/rstLst/')]/span/text()")
        categories = []
        for category in cats:
            categories.append(category.extract().strip())
        business['categories'] = categories
        telephone = selector.xpath("//div[@class='rstinfo-table']//strong[@class='rstinfo-table__tel-num']/text()")
        if telephone:
            business['telephone'] = telephone[0].extract().strip()
        stars = selector.xpath("//span[@class='rdheader-rating__score-val-dtl']/text()")[0].extract().strip()
        business['stars'] = convert_to_float_if_float(stars)

        for meal in ['dinner', 'lunch']:
            price = selector.xpath("//p[@class='rdheader-budget__icon rdheader-budget__icon--{0}']/span/a/text()".format(meal)).extract()
            if price:
                business['price_{0}'.format(meal)] = price[0]
            #stars = selector.xpath("//div[@class='score-s']/span[@class='{0}']/following-sibling::em/text()".format(meal))[0].extract()
            #stars = selector.xpath("//span[@class='rdheader-rating__score-val-dtl']/text()".format(meal))[0].extract()
            #business['stars_{0}'.format(meal)] = convert_to_float_if_float(stars)

        review_count = selector.xpath("//em[@property='v:count']/text()")
        if review_count:
            business['review_count'] = convert_to_int_if_int(review_count[0].extract())

        business['prefecture'] = re.findall(r'([a-z]+)/A\d{4}/A\d{6}/\d+/', response.url)[0]
        business['area'] = re.findall(r'[a-z]+/(A\d{4})/A\d{6}/\d+/', response.url)[0]
        business['subarea'] = re.findall(r'[a-z]+/A\d{4}/(A\d{6})/\d+/', response.url)[0]

        # business['menu_items'] = self._generate_menu_items(response)
        return business

    def _generate_menu_items(self, response):
        # TODO: implement me
        pass
