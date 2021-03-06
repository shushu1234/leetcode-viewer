# /usr/bin/env python3
"""
这是一个将力扣中国(leetcode-cn.com)上的【个人提交】的submission自动爬到本地并push到github上的爬虫脚本。
请使用相同目录下的config.json设置 用户名，密码，本地储存目录等参数。
致谢@fyears， 本脚本的login函数来自https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba
"""
import os
import time
import re
import requests
import json
from lxml import etree

requests.packages.urllib3.disable_warnings()  # 为了避免弹出一万个warning，which is caused by 非验证的get请求

leetcode_url = 'https://leetcode-cn.com/'

sign_in_url = 'accounts/login/'
sign_in_url = leetcode_url + sign_in_url
submissions_url = 'submissions/'
submissions_url = leetcode_url + submissions_url

with open("config.json", "r") as f:  # 读取用户名，密码，本地存储目录
    temp = json.loads(f.read())
    USERNAME = temp['username']
    PASSWORD = temp['password']
    OUTPUT_DIR = temp['outputDir']


file_suffix = {"cpp": "cpp", "python3": "py", "python": "py", "mysql": "sql", "golang": "go", "java": "java",
               "c": "c", "javascript": "js", "php": "php", "csharp": "cs", "ruby": "rb", "swift": "swift",
               "scala": "scl", "kotlin": "kt", "rust": "rs"}


session = requests.Session()
user_agent = r'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36'


def login(email, password):  # 本函数copy自https://gist.github.com/fyears/487fc702ba814f0da367a17a2379e8ba，感谢@fyears
    client = requests.session()
    client.encoding = "utf-8"

    while True:
        try:
            client.get(sign_in_url, verify=False)

            login_data = {'login': email,
                          'password': password
                          }

            result = client.post(sign_in_url, data=login_data, headers=dict(Referer=sign_in_url))

            if result.ok:
                print("登录成功!")
                break
        except:
            print("登录失败，请稍后再试...")
            time.sleep(5*1000)

    return client

def write_to_file(client, submission):
    Lang = submission['lang']
    submission_id = submission['id']
    submission_timestamp = submission['timestamp']
    # submission_code=submission['code']

    problem_slug = submission['problem_slug']
    # submission_code = problem['code']
    submission_code = submission['code_str']
    question = get_problem_by_slug(problem_slug)

    submission_list = get_submissions_slug(client, problem_slug)

    questionId = question['questionId']
    questionFrontendId = question['questionFrontendId']
    boundTopicId = question['boundTopicId']
    title = question['title']
    titleSlug = question['titleSlug']
    content = question['content']
    translatedTitle = question['translatedTitle']
    translatedContent = question['translatedContent']
    difficulty = question['difficulty']
    similarQuestions = json.loads(question['similarQuestions'])
    topicTags = question['topicTags']
    stats = json.loads(question['stats'])

    # 转换成localtime
    time_local = time.localtime(int(submission_timestamp))
    # 转换成新的时间格式(2016-05-05 20:28:54)
    submission_date = time.strftime("%Y-%m-%d", time_local)

    print(questionFrontendId + "-" + translatedTitle + " 开始写入...")

    content = '<div>' + content + '</div>'

    translatedContent = '<div>' + translatedContent + '</div>'

    categories = ""
    if difficulty == 'Easy':
        categories = '简单'
    elif difficulty == 'Medium':
        categories = '中等'
    elif difficulty == 'Hard':
        categories = '困难'

    filepath = OUTPUT_DIR + '/' + categories + '/' + '{:0=4}'.format(
        int(questionFrontendId)) + "-" + translatedTitle + '.md'

    with open(filepath, "w") as f:  # 开始写到本地
        # print ("Writing begins!", totalpath)
        f.writelines("---\n")
        f.writelines("title: " + questionFrontendId + "-" + translatedTitle + "(" + title + ")\n")
        f.writelines("date: " + submission_date + "\n")
        f.writelines("categories:\n")
        f.writelines("  - " + categories + "\n")
        f.writelines("tags:\n")
        if len(topicTags) > 0:
            for i in range(len(topicTags)):
                if topicTags[i]['translatedName'] != None:
                    f.writelines("  - " + topicTags[i]['translatedName'] + "<" + topicTags[i]['name'] + ">\n")
                else:
                    f.writelines("  - " + topicTags[i]['name'] + "\n")
        f.writelines("---\n")

        f.writelines("## 英文原文\n")
        f.write(content)

        f.writelines("\n\n")
        f.writelines("## 中文翻译\n")
        f.write(translatedContent)

        f.writelines("\n\n")
        f.writelines("## 通过代码\n")
        # f.writelines("```" + Lang + "\n")
        f.write(submission_code)
        # f.writelines("\n```\n")

        f.writelines("\n\n")
        solution_detail = get_solution_detail_by_node(problem_slug, get_solutions_by_slug(problem_slug,"DEFAULT"))
        if solution_detail['author']['username'] != 'LeetCode':
            solution_detail = get_solution_detail_by_node(problem_slug, get_solutions_by_slug(problem_slug, "MOST_UPVOTE"))
        solution_content = solution_detail['content']
        image_dict = download_image(problem_slug, solution_content)
        for key in image_dict:
            solution_content = solution_content.replace(key, image_dict[key])
        if solution_detail['author']['username'] == 'LeetCode':
            f.writelines("## 官方题解\n")
        else:
            f.writelines("## 高赞题解\n")
        # f.writelines("```" + Lang + "\n")
        f.write(solution_content)

        f.writelines("\n\n")
        f.writelines("## 统计信息\n")
        f.writelines("| 通过次数 | 提交次数 | AC比率 |\n")
        f.writelines("| :------: | :------: | :----: |\n")
        f.writelines("|    " + str(stats['totalAcceptedRaw']) + "    |    " + str(
            stats['totalSubmissionRaw']) + "    |   " + str(stats['acRate']) + "   |")

        if len(submission_list) > 0:
            f.writelines("\n\n")
            f.writelines("## 提交历史\n")
            f.writelines("| 提交时间 | 提交结果 | 执行时间 |  内存消耗  | 语言 |\n")
            f.writelines("| :------: | :------: | :------: | :--------: | :--: |\n")
            for i in range(len(submission_list)):
                # 转换成localtime
                time_local = time.localtime(int(submission_list[i]['timestamp']))
                # 转换成新的时间格式(2016-05-05 20:28:54)
                submission_times = time.strftime("%Y-%m-%d %H:%M:%S", time_local)
                f.writelines("|    " + submission_times + "    |    ["
                             + submission_list[i]['statusDisplay'] + "](https://leetcode-cn.com/"
                             + submission_list[i]['url'] + ")   |    "
                             + submission_list[i]['runtime'] + "    | "
                             + submission_list[i]['memory'] + " | "
                             + submission_list[i]['lang'] + "  |\n")

        if len(similarQuestions) > 0:
            f.writelines("\n\n")
            f.writelines("## 相似题目\n")
            f.writelines("|                             题目                             | 难度 |\n")
            f.writelines("| :----------------------------------------------------------: | :--: |\n")
            for i in range(len(similarQuestions)):
                similarQuestions_difficulty = ""
                if similarQuestions[i]['difficulty'] == 'Easy':
                    similarQuestions_difficulty = '简单'
                elif similarQuestions[i]['difficulty'] == 'Medium':
                    similarQuestions_difficulty = '中等'
                elif similarQuestions[i]['difficulty'] == 'Hard':
                    similarQuestions_difficulty = '困难'
                f.writelines("| [" + similarQuestions[i]['translatedTitle'] + "](https://leetcode-cn.com/problems/" +
                             similarQuestions[i]['titleSlug'] + "/) | "
                             + similarQuestions_difficulty + "|\n")

        f.close()
        print(questionFrontendId + "-" + translatedTitle + " 写入完成!\n")


def get_submissions_slug(client, slug):
    url = "https://leetcode-cn.com/graphql"
    params = {'operationName': "Submissions",
              'variables': {"offset": 0, "limit": 20, "lastKey": '', "questionSlug": slug},
              'query': '''query Submissions($offset: Int!, $limit: Int!, $lastKey: String, $questionSlug: String!) {
                submissionList(offset: $offset, limit: $limit, lastKey: $lastKey, questionSlug: $questionSlug) {
                lastKey
                hasNext
                submissions {
                    id
                    statusDisplay
                    lang
                    runtime
                    timestamp
                    url
                    isPending
                    memory
                    __typename
                }
                __typename
            }
        }'''
              }

    json_data = json.dumps(params).encode('utf8')

    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Referer': 'https://leetcode.com/accounts/login/',
               "Content-Type": "application/json"}
    resp = client.post(url, data=json_data, headers=headers, timeout=10)
    content = resp.json()
    return content['data']['submissionList']['submissions']


def get_problem_by_slug(slug):
    url = "https://leetcode-cn.com/graphql"
    params = {'operationName': "questionData",
              'variables': {'titleSlug': slug},
              'query': '''query questionData($titleSlug: String!) {
              question(titleSlug: $titleSlug) {
                questionId
                questionFrontendId
                boundTopicId
                title
                titleSlug
                content
                translatedTitle
                translatedContent
                isPaidOnly
                difficulty
                likes
                dislikes
                isLiked
                similarQuestions
                contributors {
                  username
                  profileUrl
                  avatarUrl
                  __typename
                }
                langToValidPlayground
                topicTags {
                  name
                  slug
                  translatedName
                  __typename
                }
                companyTagStats
                codeSnippets {
                  lang
                  langSlug
                  code
                  __typename
                }
                stats
                hints
                solution {
                  id
                  canSeeDetail
                  __typename
                }
                status
                sampleTestCase
                metaData
                judgerAvailable
                judgeType
                mysqlSchemas
                enableRunCode
                envInfo
                book {
                  id
                  bookName
                  pressName
                  description
                  bookImgUrl
                  pressImgUrl
                  productUrl
                  __typename
                }
                isSubscribed
                __typename
              }
            }'''
              }

    json_data = json.dumps(params).encode('utf8')

    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Content-Type': 'application/json',
               'Referer': 'https://leetcode-cn.com/problems/' + slug}
    resp = session.post(url, data=json_data, headers=headers, timeout=10)
    content = resp.json()

    # 题目详细信息
    question = content['data']['question']

    return question


def get_solutions_by_slug(slug,sortMethod):
    url = "https://leetcode-cn.com/graphql"
    params = {'operationName': "questionSolutionArticles",
              'variables': {'questionSlug': slug, 'first': 10, 'skip': 0, 'orderBy': sortMethod},
              'query': '''query questionSolutionArticles($questionSlug: String!, $skip: Int, $first: Int, $orderBy: SolutionArticleOrderBy, $userInput: String) {
               questionSolutionArticles(questionSlug: $questionSlug, skip: $skip, first: $first, orderBy: $orderBy, userInput: $userInput) {
                totalNum
                 edges {
                  node {
                   ...article
                   __typename
                   }
                 __typename
                }
                __typename
                    }
                }
                         
                fragment article on SolutionArticleNode {
                    title
                    slug
                    reactedType
                    status
                    identifier
                    canEdit
                    reactions {
                       count
                       reactionType
                       __typename
                    }
                    tags {
                        name
                        nameTranslated
                        slug
                        __typename
                    }
                    createdAt
                        thumbnail
                        author {
                            username
                            profile {
                                userAvatar
                                userSlug
                                realName
                                __typename
                            }
                            __typename
                        }
                        summary
                        topic {
                            id
                            commentCount
                            viewCount
                            __typename
                        }
                        byLeetcode
                        isMyFavorite
                        isMostPopular
                        isEditorsPick
                        upvoteCount
                        upvoted
                        hitCount
                        __typename
                    }
                '''
              }

    json_data = json.dumps(params).encode('utf8')

    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Content-Type': 'application/json',
               'Referer': 'https://leetcode-cn.com/problems/' + slug}
    resp = session.post(url, data=json_data, headers=headers, timeout=10)
    content = resp.json()

    node = content['data']['questionSolutionArticles']['edges'][0]['node']

    return node


def download_image(problem_slug, detial):
    image_dict = {}
    pattern = 'https://pic.leetcode-cn.com[\w|.|\-|\/|%|&|~|#|_|=|*]+'
    regex = re.compile(pattern)
    image_list = regex.findall(detial)
    for i in range(len(image_list)):
        r = requests.get(image_list[i])
        suffix=(image_list[i].split(".")[-1])
        image_suffix_list=['png','jpg','jpeg','gif']
        if not image_suffix_list.__contains__(suffix.lower()):
            suffix='png'
        image_name = "/images/" + problem_slug + "-" + str(i) + "." + suffix.lower()
        print("下载图片到："+image_name)
        with open(OUTPUT_DIR + image_name, 'wb') as f:
            f.write(r.content)
        image_dict[image_list[i]] = ".." + image_name
    return image_dict


def get_solution_detail_by_node(problem_slug, node):
    solution_slug = node['slug']
    url = "https://leetcode-cn.com/graphql"
    params = {'operationName': "solutionDetailArticle",
              'variables': {'slug': solution_slug},
              'query': '''query solutionDetailArticle($slug: String!) {
               solutionArticle(slug: $slug) {
                ...article
                 content
                  question {
                  questionTitleSlug
                  __typename
               }
               __typename
               }
               }
                       
               fragment article on SolutionArticleNode {
                   title
                   slug
                   reactedType
                   status
                   identifier
                   canEdit
                   reactions {
                       count
                       reactionType
                       __typename
                   }
                   tags {
                       name
                       nameTranslated
                       slug
                       __typename
                   }
                   createdAt
                   thumbnail
                   author {
                       username
                       profile {
                           userAvatar
                           userSlug
                           realName
                           __typename
                       }
                        __typename
                   }
                       summary
                       topic {
                           id
                           commentCount
                           viewCount
                           __typename
                   }
                   byLeetcode
                   isMyFavorite
                   isMostPopular
                   isEditorsPick
                   upvoteCount
                   upvoted
                   hitCount
                   __typename
                   }
               '''
              }

    json_data = json.dumps(params).encode('utf8')

    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive', 'Content-Type': 'application/json',
               'Referer': 'https://leetcode-cn.com/problems/' + problem_slug}
    resp = session.post(url, data=json_data, headers=headers, timeout=10)
    content = resp.json()

    solution_detail = content['data']['solutionArticle']

    return solution_detail


def get_submission_by_id(client, submission_id):
    url = "https://leetcode-cn.com/submissions/detail/" + str(submission_id)
    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive'}
    code_content = client.get(url, headers=headers, timeout=10)
    html = code_content.content.decode('utf-8')
    dom = etree.HTML(html)
    problem_slug = dom.xpath('//*[@id="submission-app"]/div/div[1]/h4/a/@href')[0].split('/')[2]
    code_start_index = html.index("submissionCode")
    code_end_index = html.index("editCodeUrl")
    code = html[code_start_index + 17:code_end_index - 5]
    s = code.encode()  # 此处必须进行字符串转义
    temp = s.decode('utf-8')
    pattern = "([\u4e00-\u9fa5]+|[\u3002|\uff1f|\uff01|\uff0c|\u3001|\uff1b|\uff1a|\u201c|\u201d|\u2018|\u2019|\uff08|\uff09|\u300a|\u300b|\u3008|\u3009|\u3010|\u3011|\u300e|\u300f|\u300c|\u300d|\ufe43|\ufe44|\u3014|\u3015|\u2026|\u2014|\uff5e|\ufe4f|\uffe5])"  # 中文正则表达式
    regex = re.compile(pattern)  # 生成正则对象
    results = regex.findall(temp)  # 匹配
    for result in results:  # 迭代遍历出内容
        code = code.replace(result, str(result.encode('unicode-escape'))[2:-1])
    code = code.replace("\\\\", "\\")
    code = code.encode('utf-8').decode("unicode-escape")
    lang_start_index = html.index("getLangDisplay")
    lang = html[lang_start_index + 17:code_start_index - 5]
    problem = {'problem_slug': problem_slug, 'code': code, 'lang': lang}
    return problem


def get_all_problems(client):
    url = "https://leetcode-cn.com/api/problems/all/"

    headers = {'User-Agent': user_agent, 'Connection': 'keep-alive'}
    resp = client.get(url, headers=headers, timeout=10)

    question_list = json.loads(resp.content.decode('utf-8'))
    local_problems = {}
    local_problems_code_template = {}
    exclude_problems = []
    with open("problems.json", "r") as f:  # 读取记录
        local_problems = json.loads(f.read())

    with open("code_template.json", "r") as f:  # 读取记录
        local_problems_code_template = json.loads(f.read())

    with open("exclude_problems.json", "r") as f:  # 读取记录
        exclude_problems = json.loads(f.read())
    problem_anchor = ""
    try:
        for question in question_list['stat_status_pairs']:

            question_id = question['stat']['question_id']
            frontend_question_id = question['stat']['frontend_question_id']
            # 题目状态
            question_status = question['status']

            # if question_status == 'ac' and frontend_question_id == "283":
            if question_status == 'ac':
                # 题目编号
                question_id = question['stat']['question_id']
                # 题目名称
                question_title = question['stat']['question__title']
                # 题目名称
                question_slug = question['stat']['question__title_slug']
                # 题目难度级别，1 为简单，2 为中等，3 为困难
                level = question['difficulty']['level']
                question_frontend_id = question['stat']['frontend_question_id']
                print(frontend_question_id)
                submission_list = get_submissions_slug(client, question_slug)
                problem_anchor = question_slug
                is_need_write = False
                if len(submission_list) > 0:
                    code_str = "<RecoDemo>\n"
                    if local_problems_code_template.__contains__(question_slug):
                        this_problem_code_template = local_problems_code_template[question_slug].split(",")
                        for i in range(len(this_problem_code_template)):
                            code_str += this_problem_code_template[i]
                    for i in range(len(submission_list)):
                        if int(frontend_question_id) in exclude_problems:
                            print(frontend_question_id + "-" + question_slug + " 跳过该题！")
                            break
                        if (not local_problems.__contains__(question_slug) and submission_list[i][
                            'statusDisplay'] == 'Accepted') or (
                                local_problems.__contains__(question_slug) and not local_problems[
                            question_slug].__contains__(submission_list[i]['timestamp']) and submission_list[i][
                                    'statusDisplay'] == 'Accepted'):
                            time.sleep(1)
                            temp = get_submission_by_id(client, submission_list[i]['id'])
                            this_submission_code_str = '  <template slot="code-' + temp['lang'].title() + '-' + str(
                                i + 1) + '">\n'
                            filepath = OUTPUT_DIR + '/codes/' + question_slug + '-' + str(i + 1) + '.' + file_suffix[
                                temp['lang']]
                            print("写入代码："+question_slug + '-' + str(i + 1) + '.' + file_suffix[temp['lang']])
                            with open(filepath, "w") as f:
                                f.write(temp['code'])
                            this_submission_code_str += '    <<< @/docs/views/codes/' + question_slug + '-' + str(
                                i + 1) + '.' + file_suffix[temp['lang']] + '?' + file_suffix[
                                                            temp['lang']].title() + '\n'
                            this_submission_code_str += '  </template>\n'
                            if not local_problems.__contains__(question_slug):
                                local_problems[question_slug] = submission_list[i]['timestamp']
                                local_problems_code_template[question_slug] = this_submission_code_str
                                is_need_write = True
                            if not local_problems[question_slug].__contains__(submission_list[i]['timestamp']):
                                this_problem_local_timestamp = local_problems[question_slug]
                                this_problem_local_timestamp += ',' + submission_list[i]['timestamp']
                                local_problems[question_slug] = this_problem_local_timestamp

                                this_problem_local_template = local_problems_code_template[question_slug]
                                this_problem_local_template += ',' + this_submission_code_str
                                local_problems_code_template[question_slug] = this_problem_local_template
                                is_need_write = True

                            code_str += this_submission_code_str
                    code_str += '</RecoDemo>\n'
                    submission_list[0]['title'] = question_title
                    submission_list[0]['code_str'] = code_str
                    submission_list[0]['problem_slug'] = problem_anchor

                    if is_need_write:
                        write_to_file(client, submission_list[0])
    finally:
        try:
            if problem_anchor != 'two-sum':
                local_problems.pop(problem_anchor)
                local_problems_code_template.pop(problem_anchor)
        finally:
            with open("problems.json", "w") as f:
                f.write(json.dumps(local_problems))
            with open("code_template.json", "w") as f:
                f.write(json.dumps(local_problems_code_template))


def mkdir(path):
    folder = os.path.exists(path)
    if not folder:
        os.makedirs(path)
        print("初始化文件夹成功！")


def mk_leetcode_dirs():
    mkdir("../docs/views/codes")
    mkdir("../docs/views/简单")
    mkdir("../docs/views/中等")
    mkdir("../docs/views/困难")
    mkdir("../docs/views/images")


def main():
    email = USERNAME
    password = PASSWORD

    print('正在登录...')
    client = login(email, password)
    mk_leetcode_dirs()
    get_all_problems(client)
    # node=get_solutions_by_slug('remove-all-adjacent-duplicates-in-string')
    # get_solution_detail_by_node('remove-all-adjacent-duplicates-in-string',node)


if __name__ == '__main__':
    main()
