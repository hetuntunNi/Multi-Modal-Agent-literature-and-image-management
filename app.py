from flask import Flask, render_template, request, jsonify, send_file
import os
import tempfile
from werkzeug.utils import secure_filename
import PyPDF2
from src.document_manager import DocumentManager
from src.image_manager import ImageManager

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
# 模板目录路径
template_dir = os.path.join(current_dir, 'src', 'web', 'templates')
# 静态文件目录路径
static_dir = os.path.join(current_dir, 'src', 'web', 'static')

print(f"当前目录: {current_dir}")
print(f"模板目录: {template_dir}")
print(f"静态文件目录: {static_dir}")

# 检查目录是否存在
if not os.path.exists(template_dir):
    print(f"错误: 模板目录不存在: {template_dir}")
    print("请检查目录结构是否正确")
    exit(1)

if not os.path.exists(static_dir):
    print(f"警告: 静态文件目录不存在: {static_dir}")
    os.makedirs(static_dir, exist_ok=True)
    print(f"已创建静态文件目录: {static_dir}")

# 检查index.html是否存在
index_path = os.path.join(template_dir, 'index.html')
if not os.path.exists(index_path):
    print(f"错误: index.html不存在于 {index_path}")
    print("请确保src/web/templates/index.html文件存在")
    exit(1)

app = Flask(__name__,
            template_folder=template_dir,
            static_folder=static_dir)

# 重要：增加文件上传大小限制
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# 大幅增加文件大小限制
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB 总请求大小限制
app.config['MAX_FILE_UPLOAD_SIZE'] = 100 * 1024 * 1024  # 单个文件最大100MB
app.config['MAX_BATCH_FILES'] = 20  # 批量上传最多文件数

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    'pdf': {'pdf'},
    'image': {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
}


def allowed_file(filename, file_type='pdf'):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())


def validate_pdf_file(file_path):
    """验证PDF文件是否完整有效"""
    try:
        # 检查文件是否存在且有内容
        if not os.path.exists(file_path):
            return False, "文件不存在"

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "文件为空"

        if file_size < 100:  # PDF文件通常至少有100字节
            return False, "文件大小异常"

        # 检查文件扩展名
        if not file_path.lower().endswith('.pdf'):
            return False, "文件扩展名不是PDF"

        # 检查文件头部是否为PDF
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False, "文件头部不是PDF格式"

        # 尝试打开PDF文件
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)
                if num_pages == 0:
                    return False, "PDF文件无有效页面"

                # 尝试读取第一页
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                if not text or len(text.strip()) < 10:
                    return False, "PDF文件无有效文本内容"

                return True, f"PDF文件有效，共{num_pages}页"

        except PyPDF2.errors.PdfReadError as pdf_error:
            return False, f"PDF文件损坏: {str(pdf_error)}"
        except Exception as pdf_error:
            return False, f"读取PDF失败: {str(pdf_error)}"

    except Exception as e:
        return False, f"文件验证失败: {str(e)}"


def validate_upload_files(files):
    """验证上传的文件集合"""
    if not files or all(file.filename == '' for file in files):
        return False, "没有选择文件"

    # 检查文件数量
    if len(files) > app.config['MAX_BATCH_FILES']:
        return False, f"文件数量超过限制（最多{app.config['MAX_BATCH_FILES']}个）"

    # 检查每个文件
    valid_files = []
    total_size = 0

    for file in files:
        if file.filename and allowed_file(file.filename, 'pdf'):
            # 模拟检查文件大小（注意：这里不能直接获取文件大小，需要保存后检查）
            valid_files.append(file)
        else:
            return False, f"文件 {file.filename} 不是有效的PDF文件"

    if not valid_files:
        return False, "没有有效的PDF文件"

    return True, "文件验证通过"


@app.errorhandler(413)
def too_large(e):
    """处理文件过大的错误"""
    return jsonify({
        'success': False,
        'message': f'文件太大：单个文件不能超过{app.config["MAX_FILE_UPLOAD_SIZE"] // (1024 * 1024)}MB，总请求不能超过{app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)}MB'
    }), 413


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/add_paper', methods=['POST'])
def api_add_paper():
    """添加论文API接口"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})

        file = request.files['file']
        topics = request.form.get('topics', '')

        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})

        if not topics:
            return jsonify({'success': False, 'message': '请指定分类主题'})

        if not allowed_file(file.filename, 'pdf'):
            return jsonify({'success': False, 'message': '只支持PDF文件'})

        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        # 检查文件大小
        file_size = os.path.getsize(temp_path)
        if file_size > app.config['MAX_FILE_UPLOAD_SIZE']:
            os.unlink(temp_path)
            max_size_mb = app.config['MAX_FILE_UPLOAD_SIZE'] // (1024 * 1024)
            return jsonify({'success': False, 'message': f'文件太大，不能超过{max_size_mb}MB'})

        # 验证PDF文件
        is_valid, message = validate_pdf_file(temp_path)
        if not is_valid:
            try:
                os.unlink(temp_path)
            except:
                pass
            return jsonify({'success': False, 'message': f'文件验证失败: {message}'})

        # 处理论文
        try:
            doc_manager = DocumentManager()
            topics_list = [t.strip() for t in topics.split(',')]
            result = doc_manager.add_paper(temp_path, topics_list)

            try:
                os.unlink(temp_path)
            except:
                pass

            return jsonify({'success': True, 'message': result})

        except Exception as e:
            try:
                os.unlink(temp_path)
            except:
                pass
            return jsonify({'success': False, 'message': f'处理失败: {str(e)}'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'服务器错误: {str(e)}'})


@app.route('/api/batch_add_papers', methods=['POST'])
def api_batch_add_papers():
    """批量添加论文API接口 - 优化版本"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})

        files = request.files.getlist('files')
        topics = request.form.get('topics', '')

        # 验证文件
        is_valid, message = validate_upload_files(files)
        if not is_valid:
            return jsonify({'success': False, 'message': message})

        if not topics:
            return jsonify({'success': False, 'message': '请指定分类主题'})

        # 处理每个文件
        doc_manager = DocumentManager()
        topics_list = [t.strip() for t in topics.split(',')]
        results = []
        processed_count = 0

        for file in files:
            if processed_count >= app.config['MAX_BATCH_FILES']:
                results.append({'file': file.filename, 'result': '跳过：达到批量处理上限'})
                continue

            try:
                filename = secure_filename(file.filename)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{filename}")
                file.save(temp_path)

                # 检查文件大小
                file_size = os.path.getsize(temp_path)
                if file_size > app.config['MAX_FILE_UPLOAD_SIZE']:
                    results.append({'file': filename, 'result': f'文件太大（{file_size // 1024}KB），超过限制'})
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    continue

                # 验证PDF文件
                is_valid, message = validate_pdf_file(temp_path)
                if not is_valid:
                    results.append({'file': filename, 'result': f'文件验证失败: {message}'})
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    continue

                # 处理文件
                try:
                    result = doc_manager.add_paper(temp_path, topics_list)
                    results.append({'file': filename, 'result': result})
                    processed_count += 1
                except Exception as e:
                    results.append({'file': filename, 'result': f'处理失败: {str(e)}'})

                # 清理临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass

            except Exception as e:
                results.append({'file': file.filename, 'result': f'上传失败: {str(e)}'})
                try:
                    os.unlink(temp_path)
                except:
                    pass

        success_count = len([r for r in results if '失败' not in r['result'] and '跳过' not in r['result']])
        return jsonify({
            'success': True,
            'message': f'批量处理完成：成功{success_count}个，失败{len(results) - success_count}个',
            'details': results
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'批量处理失败: {str(e)}'})


# 其他路由保持不变...
@app.route('/api/search_paper', methods=['POST'])
def api_search_paper():
    """搜索论文API接口"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        n_results = data.get('n_results', 5)

        if not query:
            return jsonify({'success': False, 'message': '请输入搜索查询', 'results': []})

        doc_manager = DocumentManager()
        results = doc_manager.search_paper(query, n_results)

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'message': f'搜索失败: {str(e)}', 'results': []})


@app.route('/api/search_image', methods=['POST'])
def api_search_image():
    """搜索图像API接口"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        n_results = data.get('n_results', 5)

        if not query:
            return jsonify({'success': False, 'message': '请输入图像描述', 'results': []})

        img_manager = ImageManager()
        results = img_manager.search_image(query, n_results)

        return jsonify({'success': True, 'results': results})

    except Exception as e:
        return jsonify({'success': False, 'message': f'搜索失败: {str(e)}', 'results': []})


@app.route('/api/validate_pdf', methods=['POST'])
def api_validate_pdf():
    """验证PDF文件API"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})

        if not allowed_file(file.filename, 'pdf'):
            return jsonify({'success': False, 'message': '只支持PDF文件'})

        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        # 验证PDF文件
        is_valid, message = validate_pdf_file(temp_path)

        # 清理临时文件
        try:
            os.unlink(temp_path)
        except:
            pass

        if is_valid:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})

    except Exception as e:
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'})


import urllib.parse


@app.route('/api/get_image')
def api_get_image():
    """获取图片文件API - 修正版本"""
    try:
        image_path = request.args.get('path')
        if not image_path:
            return jsonify({'success': False, 'message': '缺少图片路径参数'}), 400

        # URL解码路径
        image_path = urllib.parse.unquote(image_path)

        # 安全检查：确保路径存在且是有效图片文件
        if not os.path.exists(image_path):
            return jsonify({'success': False, 'message': f'图片文件不存在: {image_path}'}), 404

        # 检查文件类型
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'message': f'不支持的文件类型: {file_ext}'}), 400

        # 设置正确的MIME类型
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }

        return send_file(image_path, mimetype=mime_types.get(file_ext, 'image/jpeg'))

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取图片失败: {str(e)}'}), 500


@app.route('/api/check_image_exists')
def api_check_image_exists():
    """检查图片是否存在"""
    try:
        image_path = request.args.get('path')
        if not image_path:
            return jsonify({'exists': False})

        image_path = urllib.parse.unquote(image_path)
        exists = os.path.exists(image_path)

        return jsonify({'exists': exists, 'path': image_path})

    except Exception as e:
        return jsonify({'exists': False, 'error': str(e)})


@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'ok', 'message': '服务正常运行'})


if __name__ == '__main__':
    print("=" * 50)
    print("多模态AI智能文献与图像管理助手")
    print("=" * 50)
    print(f"启动目录: {current_dir}")
    print(f"模板目录: {template_dir}")
    print(f"静态文件目录: {static_dir}")
    print(f"文件上传限制: 单个文件最大{app.config['MAX_FILE_UPLOAD_SIZE'] // (1024 * 1024)}MB")
    print(f"批量文件限制: 最多{app.config['MAX_BATCH_FILES']}个文件")
    print("启动Flask应用...")
    print("访问地址: http://localhost:5000")

    # 使用生产级服务器以获得更好的性能
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)