String.prototype.tmp = function(obj) {
    return this.replace(/\$\w+\$/g, function(matchs) {
        var returns = obj[matchs.replace(/\$/g, "")];
        return (returns + "") == "undefined"? "": returns;
    });
};

var lucky_stuff = {
		type:1,
		title:'',
		shade:'background-color: rgba(0,0,0,.2)',
		style:'margin-top:0.4rem;padding:0.4rem 0.6rem;background-color: #dcf6fb;border: 1px solid #66d9ef;width: 86%;height:80%;border-radius:10px;font-size:0.6rem;color:#2d597c;border-radius: 10px;',
		className:'activity-dialog-close rule-box',
		time:1,
		content:''
}

$(function(){
	// ajax过渡动画
	var loading_index = null;
	 $("#loading").ajaxStart(function(){
		 loading_index = layer.open({type: 2,content:'抽奖中...'});
	 });
	 $("#loading").ajaxStop(function(){
	   layer.close(loading_index)
	 });

	// 规则
	var layer_index = null;
	var rule_box = {
			type:1,
			title:'',
			shade:'background-color: rgba(0,0,0,.2)',
			style:'margin-top:0.4rem;padding:0.4rem 0.6rem;background-color: #dcf6fb;border: 1px solid #66d9ef;width: 86%;height:80%;border-radius:10px;color:#2d597c;border-radius: 10px;',
			className:'activity-dialog-close rule-box',
			content:'<p style="font-weight: bold;">活动详情：</p><p style="color: red;">活动截止日期：2017年12月31日</p><p>1，活动期间可进行转盘抽奖，每转1次奖励1点幸运值，并使开奖进行条增加1条。</p><p>2，开奖进度条满时，从本期参与幸运用户中抽取1名进行宝物奖励（幸运值越大，中奖几率越大）。</p><p>3，获得实物奖励的玩家将收到游戏系统邮件通知，点击--往期奖励填写个人信息发放奖励。届时游戏客服人员将电话与您合适所提交的信息，并在15个工作日内发放奖励。</p><p>疑问请加入官方Q2群咨询：182989736</p><span class="dialog-box-close">&nbsp;</span>'
	}
	//弹出一个页面层
	$('#rule_box').on('click', function(){
	  //自定义标题风格
		layer_index = layer.open(rule_box)
		$('.dialog-box-close').on('click', function(){
			layer.close(layer_index)
		})
	});

	// 历史记录
	var history_box = {
					type:1,
		  			title:'',
			  	    shade:'background-color: rgba(0,0,0,.2)',
			  	    className:'dialog-box',
			  	    style:'border-radius: 10px;width:80%;height:90%;margin-top:0.4rem;',
  					content:''
		}
	var layer_history_my = null;
	$('body').on('click','.dialog-box-close', function(){
						layer.close(layer_history_my)
					})
	$('#my-win').on('click', function(){
		//自定义标题风格
		$.getJSON('wheel/history',{
				uid:$(this).data('uid'),
				d:new Date().getTime()
			},function(data){
				if(data.code == 0){
						var htmlList = '',
						htmlTemp = $("#my_win_tpl").html();
						data.ext.lists.forEach(function(object) {
							htmlList += htmlTemp.tmp(object);
						});
						history_box.content = '<div class="dialog-lists" style="overflow-y: auto;height: 13rem;"><p class="grad" style="color: red;">中奖期数<span>奖励内容</span></p>'
						history_box.content = history_box.content + htmlList
						history_box.content = history_box.content + '<span class="dialog-box-close">&nbsp;</span></div>'
						layer_history_my = layer.open(history_box)



				}else{
					alert('获取我的记录失败')
				}
			})



	})
	var layer_history_list = null
	$('body').on('click','.dialog-box-close', function(){
						layer.close(layer_history_list)
					})
	$('#win-history-score').on('click', function(){
		//自定义标题风格
		$.getJSON('wheel/history',{
				d:new Date().getTime()
			},function(data){
				if(data.code == 0){
						var htmlList = '',
						htmlTemp = $("#history_tpl").html();
						data.ext.lists.forEach(function(object) {
							htmlList += htmlTemp.tmp(object);
						});
						history_box.content = '<div class="dialog-lists" style="overflow-y: auto;height: 13rem;">'
						history_box.content = history_box.content + htmlList
						history_box.content = history_box.content + '</div><div class="user_profile"><span>(请获得实物玩家填写个人信息领取奖励)</span>&nbsp;&nbsp;&nbsp;<a href="#" id="user_profile_info"><img src="/web/static/assets/images/user_profile_btn.png"></a></div><span class="dialog-box-close">&nbsp;</span>'

						layer_history_list = layer.open(history_box)



				}else{
					alert('获取历史记录失败')
				}
			})
	})
	var user_profile = {
			type:1,
			title:'',
			shade:'background-color: rgba(0,0,0,.2)',
			style:'border: 1px solid #d4390c;color:#d4390c;padding:0.6rem;width:70%;border-radius: 10px;',
			className:'activity-dialog-close rule-box',
			content:'<p>亲，你还没有获得“实物”奖励哦，无需领取操作，赶快去参加活动吧！</p><span class="dialog-box-close">&nbsp;</span>'
	}
	var user_profile_index = null
	$('body').on('click','#user_profile_info',function(){
		user_profile_index = layer.open(user_profile)
		$('.dialog-box-close').on('click',function(){
			layer.close(user_profile_index)
		})
	})
})