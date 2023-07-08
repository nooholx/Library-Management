import pymysql
import re
import dbconfig

cust_info = []     # 회원가입 시 입력정보를 저장할 변수
check_result = []  # 현재 로그인 한 고객의 정보
rent_id = 1        # 대여목록 순번


class DB():
    # DB 초기화
    conn = None
    cursor = None
    @classmethod
    def connect(cls):
        # DB 생성
        cls.conn = pymysql.connect(
            host=dbconfig.host, user=dbconfig.user, password=dbconfig.password,
            db=dbconfig.db, charset='utf8')
        # 커서 획득
        cls.cursor = cls.conn.cursor()
        return cls.conn, cls.cursor
    @classmethod
    def commit(cls):
        cls.conn.commit()
    @classmethod
    def disconnect(cls):
        cls.cursor.close()
        cls.conn.close()


# 도서 반납
def return_rent(main_user_num, check_result):
    check_num = 0
    print("[ 도서 반납하기 ]")

    conn, cursor = DB.connect()

    sql = '''    
        SELECT rent_id, book_num, lib_name, book_name, author, rent_date, return_date
        FROM rent_list
        WHERE cust_id = %s
        ORDER BY rent_date ASC
        '''
    cursor.execute(sql, (check_result[0]))
    result = cursor.fetchall()

    # rent_list 테이블(대여목록)에 데이터가 0개일 때
    if result == ():
        print("반납할 도서가 없습니다.")
        return

    print('(등록번호, 소장도서관, 책이름, 지은이, 출판사, 대여가능여부)')

    # rent_list 테이블(대여목록)에 데이터가 있을 경우
    for i in range(len(result)):
        print(result[i], end='\n')

    user_id = input("반납할 도서의 등록번호를 입력하세요: ")


    for i in range(len(result)):
        if user_id == result[i][1]:
            check_num = 1
            return_book_num = result[i][1]
            return_book_name = result[i][3]

    if check_num == 1:
        sql2 = '''
                DELETE FROM rent_list 
                WHERE book_num = %s
                '''
        cursor.execute(sql2, (user_id))
        DB.commit()

        # book_list 테이블(도서목록)의 borrow열을 Y로 변경 ( Y : 대여가능)
        sql3 = '''
            UPDATE book_list SET
            borrow = %s WHERE book_num = %s
            '''
        print(f"등록번호 : {return_book_num}, 도서명 : {return_book_name} 을 반납하였습니다. ")

        cursor.execute(sql3, ('Y', (user_id)))
        DB.commit()
    else:
        print("대여 목록에 없는 등록번호 입니다.")

    DB.disconnect()


# cart 테이블(장바구니)에 있는 목록 출력 후 대여 여부 선택
# 매개변수 check_result는 현재 로그인한 cust의 정보
def book_rent(check_result):

    global rent_id

    # cart(장바구니) 목록을 출력하는 함수 호출
    cart_check = print_cart(check_result)
    if cart_check == -1:
        return

    input_bookid = input("대여할 도서의 등록번호를 입력하세요: ")

    conn, cursor = DB.connect()

    count_sql = f'''
                SELECT cust_id, count(*) as count
                FROM rent_list
                WHERE rent_list.cust_id like ('{(check_result[0])}')
                GROUP BY cust_id
               '''
    cursor.execute(count_sql)
    count_result = cursor.fetchall()


    # cust_id당 대여 권수 5권 이하로 제한
    if count_result == () or count_result[0][1] <= 4:

        # rent_list에 데이터 넣기 위해서 book_list에서 가져올 수 있는 col명들 select
        sql = '''
                SELECT book_num, lib_name, book_name, author, publisher, borrow
                FROM book_list
                WHERE book_num LIKE CONCAT(%s)
                '''
        cursor.execute(sql, (input_bookid))
        result = cursor.fetchone()


        # rent_id 길이 구하기
        sql2 = '''    
                SELECT rent_id
                FROM rent_list
                '''
        cursor.execute(sql2)
        rent_id = len(cursor.fetchall()) + 1


        try:
            sql3 = '''
                    INSERT INTO rent_list (rent_id, book_num, lib_name, book_name, cust_id,
                    author, publisher, rent_date, return_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL 5 DAY))
                    '''

            cursor.execute(sql3, (rent_id, result[0], result[1], result[2], check_result[0],
                                  result[3], result[4]))
            DB.commit()
            print(f"등록번호 : {result[0]}, 도서명 : {result[2]} 을 대여하였습니다.")

            # 대여 완료시 book_list 테이블(도서목록)의 borrow열을 N으로 변경
            sql4 = '''
                        UPDATE book_list SET
                        borrow = %s WHERE book_num = %s
                        '''
            cursor.execute(sql4, ('N', (input_bookid)))
            DB.commit()

            # cart 테이블(장바구니)에서 삭제
            sql5 = '''
                    DELETE FROM cart 
                    WHERE book_num = %s
                    '''
            cursor.execute(sql5, (result[0]))  # result[0] = book_num
            DB.commit()

        except Exception as err:
            if err.args[0] == 1062:
                print("이미 대여한 등록번호입니다. 다른 책을 대여해주세요.")

            else:
                print("해당 등록번호를 찾을 수 없습니다.")

        finally:
            DB.commit()
            DB.disconnect()
    else:
        print("1인당 대여가능한 권수(5권)를 초과하였습니다.")


# cart 테이블(장바구니)을 출력하는 함수
def print_cart(check_result):
    conn, cursor = DB.connect()

    sql = ''' 
          SELECT * 
          FROM cart 
          WHERE cust_id = %s
          '''
    cursor.execute(sql, (check_result[0]))
    result = cursor.fetchall()

    print("[ 장바구니 ]")

    if result == ():
        print("장바구니에 담긴 도서가 없습니다.")
        return -1

    for i in range(len(result)):
        print(result[i], end='\n')

    DB.disconnect()


# 도서대여 화면 출력 함수
def print_rent(main_user_num):
    try:

        rent_user_num = 0

        while rent_user_num != 3:
            print("-----------------------------")
            print("     [ 도서대여 ]")
            print("")
            print("     1. 대여하기")
            print("     2. 뒤로가기")
            print("")
            print("-----------------------------")

            rent_user_num = int(input("입력: "))

            if rent_user_num == 1:
                book_rent(check_result)
            elif rent_user_num == 2:
                print("메인화면으로 돌아갑니다.")
                return

    except (ValueError, TypeError) as error:
        print('올바르지 않은 입력입니다. 다시 입력해 주세요.')

    else:
        print("잘못된 입력입니다. 1~2의 숫자를 입력해주세요.")


# 등록번호 검색 함수
def search_bookNum(check_result):
    print("등록번호검색을 선택하였습니다.")
    input_bookNum = input("등록번호를 입력하세요: ")

    conn, cursor = DB.connect()

    sql = '''
        SELECT book_id, lib_name, ref_lib, book_num, book_name, author, publisher, borrow 
        FROM book_list 
        WHERE book_num LIKE CONCAT(%s)
        '''

    cursor.execute(sql,(input_bookNum))
    result = cursor.fetchall()

    if result == ():
        print("해당 등록번호를 찾을 수 없습니다.")
        DB.disconnect()
        return

    print('(연번, 소장도서관, 자료실명, 등록번호, 책이름, 지은이, 출판사, 대여가능여부)')
    print(result)

    cart = input("장바구니에 넣겠습니까? 1.예 2.아니요 : ")

    if result[0][7] == 'N':
        print("현재 대여중인 도서입니다.")
        return

    # borrow : Y일 경우
    if int(cart) == 1:
        try:
            sql2 = '''
                INSERT INTO cart (book_num, book_name, author, cust_id)
                VALUES (%s, %s, %s, %s)
                '''
            cursor.execute(sql2, (result[0][3], result[0][4], result[0][5], check_result[0]))
            print(f"등록번호 : {result[0][3]}, 도서명 : {result[0][4]} 을 장바구니에 추가하였습니다.")

        except Exception as err:
            if err.args[0] == 1062:
                print("중복된 등록번호입니다. 다른 책을 장바구니에 넣어주세요")
            if err.args[0] == 1644:
                print("대여 가능한 권수를 초과하였습니다. (1인 최대 5권 대여 가능)")

        finally:
            DB.commit()
            DB.disconnect()
    else:
        print("잘못된 입력입니다.")
        return

# 도서명 검색 함수
def search_author():
    print("저자명검색을 선택하였습니다.(도서를 찾으셨으면, 초기화면의 3번으로 가서 조회하세요)")
    user_author = input("저자명을 입력하세요: ")

    conn, cursor = DB.connect()

    sql = f'''
        SELECT book_id, lib_name, ref_lib, book_num, book_name, author, publisher, borrow
        FROM book_list
        WHERE author LIKE CONCAT('%%', %s, '%%')
        '''
    cursor.execute(sql, (user_author))
    result = cursor.fetchall()

    if result == ():
        print("해당 저자명을 찾을 수 없습니다.")
        return

    print('(연번, 소장도서관, 자료실명, 등록번호, 책이름, 지은이, 출판사, 대여가능여부)')
    for i in range(len(result)):
        print(result[i], end='\n')

    DB.disconnect()


# 저자명 검색 함수
def search_name():
    print("도서명검색을 선택하였습니다. (도서를 찾으셨으면, 초기화면의 3번으로 가서 조회하세요)")
    user_book = input("도서명을 입력하세요: ")

    conn, cursor = DB.connect()

    sql = f''' 
        SELECT book_id, lib_name, ref_lib, book_num, book_name, author, publisher, borrow
        FROM book_list
        WHERE book_name LIKE CONCAT('%%', %s, '%%')
        '''
    cursor.execute(sql, (user_book))
    result = cursor.fetchall()

    if result == ():
        print("해당 도서명을 찾을 수 없습니다.")
        return

    print('(연번, 소장도서관, 자료실명, 등록번호, 책이름, 지은이, 출판사, 대여가능여부)')
    for i in range(len(result)):
        print(result[i], end='\n')

    DB.disconnect()


# 도서조회 화면 출력 함수
def print_search(num):
    global check_result
    try:
        while True:
            print("-----------------------------")
            print("      「 소장자료 검색 」")
            print("     1. 도서명으로 검색")
            print("     2. 저자명으로 검색")
            print("     3. 장바구니 담기\n        (등록번호 입력)")
            print("     4. 뒤로가기")
            print("-----------------------------")
            book_list_num = int(input("입력: "))

            if book_list_num == 1:
                search_name()

            elif book_list_num == 2:
                search_author()

            elif book_list_num == 3:
                search_bookNum(check_result)

            elif book_list_num == 4:
                print("메인메뉴로 돌아가기")
                break

            else:
                print('잘못 입력하였습니다. 1~4사이의 수를 입력하세요')

    except (ValueError, TypeError) as error:
        print('올바르지 않은 입력입니다. 다시 입력해 주세요.')

    else:
        if num == 4:
            print("뒤로 돌아갑니다.")
            return


# 메인 메뉴 출력 함수
def print_main():
    try:
        main_user_num = 0

        while main_user_num != 5:

            print("원하시는 메뉴를 선택하세요")
            print("-----------------------------")
            print("      도서 메뉴")
            print("     1. 도서조회")
            print("     2. 도서대여")
            print("     3. 도서반납")
            print("     4. 장바구니")
            print("     5. 뒤로가기")
            print("-----------------------------")

            main_user_num = int(input("입력: "))

            if main_user_num == 1:
                print("도서조회를 선택하였습니다")
                print_search(main_user_num)  # 도서조회 메뉴 출력 함수 호출
            elif main_user_num == 2:
                print("도서대여를 선택하였습니다")
                print_rent(main_user_num)
            elif main_user_num == 3:
                print("도서반납을 선택하였습니다")
                return_rent(main_user_num, check_result)
            elif main_user_num == 4:
                print("장바구니를 확인합니다")
                print_cart(check_result)
            elif main_user_num == 5:
                print("로그아웃 되었습니다.")
                return
            else:
                print("잘못된 입력입니다. 1~5의 숫자를 입력해주세요.")
    except (ValueError, TypeError) as error:
        print('올바르지 않은 입력입니다. 로그아웃 되었습니다.')



# 비밀번호 일치여부를 확인하는 함수
def check_PWD(input_id, input_pwd, check_result):
    if check_result[0] == input_id and check_result[1] == input_pwd:
        print("로그인 되었습니다.")
        print_main()
        return check_result
    else:
        print(f"아이디 또는 비밀번호가 일치하지 않습니다.")


# 아이디 존재 여부를 확인하는 함수
def check_ID(input_id):
    global check_result
    check = 0

    while check != 1:

        conn, cursor = DB.connect()
        sql = '''SELECT * FROM member_info'''
        cursor.execute(sql)
        result = cursor.fetchall()

        for i in range(len(result)):
            check_result = result[i]
            if result[i][0] == input_id:
                check = 1
                DB.disconnect()
                return check_result

        if check == 0:
            print(f"존재하지 않는 아이디입니다.")
            DB.disconnect()
            return -1


# 로그인 함수
def account_login():
    print("[ 로그인 ]")
    input_id = input("id를 입력하세요 : ")
    input_pwd = input("pw를 입력하세요 : ")

    # user가 입력한 id가 DB에 있는지 확인하는 함수 호출한 후 return 값(있으면 행(row)정보, 없으면 -1)을 return_id에 저장
    return_id = check_ID(input_id)
    if return_id != -1:
        check_PWD(input_id, input_pwd, return_id)


# 회원가입 함수
def join_member():
    global cust_info
    check = 0

    print(f"[ 회원가입하기 ]")

    while check != 1:

        conn, cursor = DB.connect()
        print("ID는 영어와 숫자로만 입력될 수 있습니다. 시작 문자는 영어이어야 합니다.")
        cust_id = input("ID를 입력하세요 : ")

        # ID는 영어 소문자로 시작 규칙 지정
        pattern1 = re.compile('[a-z]')
        # 숫자, 영소문자를 제외한 문자가 있다면 ture / 없으면 false
        pattern2 = re.compile('[^0-9a-z]]')
        result1 = pattern1.match(cust_id)
        result2 = pattern2.search(cust_id)

        if result1 and not result2:
            print(f"{cust_id} 가입이 가능한 ID입니다.")
        else:
            print(f"{cust_id} 가입이 불가능한 아이디입니다.")
            return

        sql = '''SELECT cust_id FROM member_info'''
        cursor.execute(sql)
        result = cursor.fetchall()

        for i in range(len(result)):
            if result[i][0] == cust_id:
                print("이미 가입된 ID입니다.")
                check = 1

        if check == 0:
            cust_info.append(cust_id)
            print(f"PW를 입력하세요 : ")
            cust_pw = input()
            cust_info.append(cust_pw)
            print(f"핸드폰 번호를 입력하세요(숫자만 입력) : ")
            cust_phone = input()
            cust_info.append(cust_phone)

            sql = '''
                INSERT INTO member_info (cust_id, cust_pw, phone_number)
                VALUES (%s, %s, %s)
                '''
            cursor.execute(sql, (cust_info[0], cust_info[1], cust_info[2]))
            DB.commit()
            DB.disconnect()
            # cust_info 초기화
            cust_info = []
            break
