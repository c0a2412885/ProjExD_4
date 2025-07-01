import math
import os
import random
import sys
import time
import pygame as pg 


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  #右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  #右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  #上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  #左上
            (-1, 0): img0,
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  #左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  #下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  #右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = -1

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life < 0:
                self.state = "normal"
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)   # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird, angle: float = 0):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        base_angle = math.degrees(math.atan2(-bird.dire[1], bird.dire[0]))
        total_angle = base_angle + angle
        self.vx = math.cos(math.radians(total_angle))
        self.vy = -math.sin(math.radians(total_angle))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), total_angle, 1.0)
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class NeoBeam:
    @staticmethod
    def gen_beams(bird: Bird, num: int) -> list[Beam]:
        start = -50
        end = +50
        step = (end - start) // (num - 1)
        angles = range(start, end + 1, step)
        return [Beam(bird, angle) for angle in angles]



class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """:
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]

    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class EMP:
    """
    電磁パルス効果を処理するクラス
    """
    def __init__(self, enemy_group: pg.sprite.Group, bomb_group: pg.sprite.Group, screen: pg.Surface):
        self.screen = screen
        self.timer = 3
        self.active = True

        for enemy in enemy_group:
            enemy.interval = float("inf")
            enemy.image = pg.transform.laplacian(enemy.image)

        for bomb in bomb_group:
            bomb.speed /= 2
            bomb.inactive = True

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.active = False

    def draw(self):
        flash = pg.Surface((WIDTH, HEIGHT))
        flash.set_alpha(100)
        flash.fill((255, 255, 0))
        self.screen.blit(flash, (0, 0))


class Shield(pg.sprite.Sprite):
    """
    シールドを発生させるクラス
    """

    def __init__(self, bird: Bird, life: int):
        super().__init__()
        self.life=life
        self.image=pg.Surface((bird.rect.height*2, bird.rect.height*2))#サーフェスを作成
        pg.draw.rect(self.image, (0, 0, 255), pg.Rect(0, 0, 20, bird.rect.height*2))
        self.rect=self.image.get_rect()
        self.image.set_colorkey((0,0,0))#黒い部分を透明化
        self.vx, self.vy=bird.dire
        direction=math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotate(self.image, direction)#求めた角度で回転
        self.rect.centerx = bird.rect.centerx+self.rect.width*self.vx
        self.rect.centery = bird.rect.centery+self.rect.height*self.vy
    
    def update(self):
        self.life-=1
        if self.life < 0:
            self.kill()



class gravity(pg.sprite.Sprite):
    """
    重力場を全画面に表示するクラス
    """
    def __init__(self, life: int):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.fill((0,0,0))
        self.image.set_alpha(128)
        self.rect = self.image.get_rect()
        self.life = life
        
    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emp_effect = None
    shields = pg.sprite.Group()
    gravitys = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    score.value=100
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return
            
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    if key_lst[pg.K_LSHIFT]:
                        for b in NeoBeam.gen_beams(bird, 5):  # ビーム5本
                            beams.add(b)
                    else:
                            beams.add(Beam(bird))

                if event.key == pg.K_RETURN and score.value >= 200:
                    gravitys.add(gravity(400))
                    score.value -= 200
                if event.key == pg.K_e and score.value >= 20 and emp_effect is None:
                    emp_effect = EMP(emys, bombs, screen)
                    score.value -= 20

            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT and score.value >= 100:
                bird.state = "hyper"
                bird.hyper_life = 500
                score.value -= 100

            if (score.value >= 50) and (event.type == pg.KEYDOWN and event.key == pg.K_s):
                shields.add(Shield(bird, 400))
                score.value-=50
        screen.blit(bg_img, [0, 0])

        if emp_effect:
            emp_effect.update()
            emp_effect.draw()
            if not emp_effect.active:
                emp_effect = None

        if tmr % 200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        if len(gravitys) > 0:
                    for bomb in bombs:
                        exps.add(Explosion(bomb, 30))
                        score.value += 1
                    bombs.empty()

                    for emy in emys:
                        exps.add(Explosion(emy, 50))
                        score.value += 10
                    emys.empty()

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            if hasattr(bomb, "inactive") and bomb.inactive:
                continue
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1
            else:
                bird.change_img(8, screen)  # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        
        for bomb in pg.sprite.groupcollide(bombs, shields, True, True).keys():#シールドと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))


        bird.update(key_lst, screen)
        gravitys.update()
        gravitys.draw(screen)
        beams.update()
        beams.draw(screen)
        emys.update() 
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        shields.update()
        shields.draw(screen)
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
    