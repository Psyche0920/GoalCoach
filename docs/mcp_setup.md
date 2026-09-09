## Setting up MCPs

### agy - Antigravity CLI
1. run: /mcp inside agy and authenticate notion
2. for jira (we connect through composio):
-  sign up or log in on https://dashboard.composio.dev/
- from the left side menu bar, choose "connect apps"
- connect to jira
- from the same menu bar, choose "connect my agent"
- choose antigravity from the list, go in the page and copy the api key
- replace `$(COMPOSIO_API_KEY)` with the api key in the .agents/mcp_config.json file
- go to terminal, go inside agy, run : /mcp
- authenticate composio
- next, inside agy, run: composio add jira
3. another option to connect jira (but not very useful):
- this mcp doesnt provide much mcp tools, if you wish to connect it anyways, you can read this or not:
https://support.atlassian.com/atlassian-ai-gateway/docs/configure-authentication-via-api-token/
- to connect, first, create api key: https://id.atlassian.com/manage-profile/security/api-tokens?autofillToken&expiryDays=max&appId=mcp-v2&selectedScopes=all
- and then run in terminal
```
echo -n "`your.email@example.com`:`YOUR_API_TOKEN_HERE`" | base64
```
- copy the result in terminal and replace `$(API_KEY_64)` with it in the mcp_config.json file 
- (note: now config is using https://mcp.atlassian.com/v2/mcp?tools=all, and there are not much mcp tools we can use with this. i tried to connect to this https://mcp.atlassian.com/v2/mcp but it failed everytime because of denied access. even though the same link has no problem for opencode and it works for opencode)
4. check status with either /mcp inside agy or run in terminal
```
agy mcp list
```

---
### opencode
1. run in terminal:
```
opencode mcp auth notion
```
```
opencode mcp auth atlassian
```
2. check status
```
opencode mcp list
```