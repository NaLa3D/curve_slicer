# Curve View Trimmer

**Curve View Trimmer** は、Blenderの3Dビュー上で手描きしたアノテーション（ペン線）に沿って、視線（ビュー）方向にメッシュを直感的にトリム（削り落とし）できるアドオンです。

---

## 🌟 主な特徴

- ✏️ **直感的なトリム**: 視点から線を描くだけで、削り取る領域を即座にリボン化
- 🎯 **対象オブジェクトの選択**: スポイトで削りたいオブジェクトを直接指定可能
- 🔄 **消去方向の反転**: どちら側を削るかをワンクリックで切り替え（Flip）
- 📐 **リボン幅のリアルタイム調整**: スライダーで削る太さを確認しながら調整可能
- 🛡️ **安定したブーリアン処理**: 高精度（Exact）と高速（Fast）の自動切り替えにより不発を防止

---

## ⚠️ 重要な使い方・コツ

> [!IMPORTANT]
> **アノテーションの線は、必ずオブジェクトの外側（輪郭の外）まで突き抜けるように描いてください！**
> オブジェクトの内側で線が途切れていると、綺麗に切り落とせなかったり穴が開く原因になります。削り落としたい境界を完全に横切るように長めに描くのが綺麗にトリムするコツです。

---

## 📖 使い方

### 1. 対象オブジェクトの指定
- 3Dビューのサイドバー（Nキー） > **「Curve Slicer」** タブを開きます。
- 「トリム対象オブジェクト」のスポイトをクリックし、削りたい立体を選択します（未指定の場合は現在選択中のオブジェクトが対象になります）。

### 2. ビュー視点を決めて線を描く
- 削りたい角度に3Dビューの視点を合わせます。
- **`Dキー + 左ドラッグ`** で、削り落としたい「キワ」に沿って線を描きます。
  - ※ 描き直したい部分がある場合は **`Dキー + 右ドラッグ`** で部分消去（消しゴム）できます。

### 3. リボン化 ＆ 向き・幅の調整
- **「① ペンの線をリボン化」** をクリックします。
- 削る向きが逆の場合は **「🔄 消す向きを反転 (Flip)」** を押します。
- 必要に応じて「リボンの幅」スライダーで削る太さを調整します。

### 4. トリム実行
- **「② トリム実行（ビュー方向に消去！）」** をクリックします。
- ビュー方向に沿ってオブジェクトがスッキリ削り落とされます！

---

## ⚙️ 動作環境

- **Blender 4.5 以降**
- OS: Windows / macOS / Linux

---

## 📥 インストール方法

1. 本ページの緑色のボタン **「Code」 > 「Download ZIP」** をクリックしてダウンロードします。
2. ダウンロードした ZIP ファイルを **右クリックして「すべて展開（解凍）」** します。
3. Blender を起動し、**編集 > プリファレンス > アドオン** を開きます。
4. 右上の **「インストール... (Install...)」** をクリックします。
5. 解凍したフォルダ内にある **`curve_slicer.py`**（Pythonファイル）を選択してインストールします。
   - ※ ZIPファイルのままだと正常に認識されない場合があるため、必ず解凍して `.py` ファイルを選択してください。
6. 一覧に表示された **「Curve View Trimmer」** にチェックを入れて有効化します。

---

## 👤 作者 (Author)

- **NaLa**

---

## 🌐 English Summary

**Curve View Trimmer** is a Blender add-on that allows you to intuitively trim/carve 3D meshes along your 3D viewport's view direction using freehand annotation strokes.

### Installation
1. Click **Code > Download ZIP** and **unzip** the downloaded archive.
2. In Blender, go to **Edit > Preferences > Add-ons > Install...**
3. Select the unzipped **`curve_slicer.py`** file and enable it.

### Quick Workflow
1. Select your target mesh using the eyedropper picker.
2. Draw your cutting line across the object using `D + Left Drag` (Erase with `D + Right Drag`).
   - *Note: Make sure your stroke extends completely beyond the object's silhouette.*
3. Click **Convert Annotation to Ribbon** and adjust direction (Flip) / width if needed.
4. Click **Execute Trim** to carve out the mesh along the view direction.
