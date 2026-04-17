package com.ruoyi.qingbird.domain;

import com.ruoyi.common.annotation.Excel;
import com.ruoyi.common.core.domain.BaseEntity;

/**
 * 云文档文章对象 biz_cloud_doc
 * 
 * @author ruoyi
 * @date 2026-04-14
 */
public class BizCloudDoc extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    /** 文章ID */
    private Long id;

    /** 文章标题 */
    @Excel(name = "文章标题")
    private String title;

    /** 文章分类（字典键值） */
    @Excel(name = "文章分类")
    private String category;

    /** 富文本内容 */
    private String content;

    /** 状态（0正常 1隐藏） */
    @Excel(name = "状态", readConverterExp = "0=正常,1=隐藏")
    private String status;

    public void setId(Long id) 
    {
        this.id = id;
    }

    public Long getId() 
    {
        return id;
    }
    public void setTitle(String title) 
    {
        this.title = title;
    }

    public String getTitle() 
    {
        return title;
    }
    public void setCategory(String category) 
    {
        this.category = category;
    }

    public String getCategory() 
    {
        return category;
    }
    public void setContent(String content) 
    {
        this.content = content;
    }

    public String getContent() 
    {
        return content;
    }
    public void setStatus(String status) 
    {
        this.status = status;
    }

    public String getStatus() 
    {
        return status;
    }

    @Override
    public String toString() {
        return "BizCloudDoc{" +
            "id=" + id +
            ", title='" + title + '\'' +
            ", category='" + category + '\'' +
            ", content='" + content + '\'' +
            ", status='" + status + '\'' +
            '}';
    }
}
